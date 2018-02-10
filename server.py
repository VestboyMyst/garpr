from bson.objectid import ObjectId
from datetime import datetime, timedelta
from flask import Flask, request, Response, jsonify
from flask.ext import restful
from flask.ext.restful import reqparse, abort

from pymongo import MongoClient

import re
import sys

import alias_service
import model as M
import rankings

from config.config import Config
from dao import Dao
from scraper.tio import TioScraper
from scraper.challonge import ChallongeScraper
from scraper.smashgg import SmashGGScraper

TYPEAHEAD_PLAYER_LIMIT = 20
BASE_REGION = 'newjersey'


# parse config file
config = Config()

mongo_client = MongoClient(host=config.get_mongo_url())
print "parsed config: ", config.get_mongo_url()

app = Flask(__name__)
api = restful.Api(app)


def err(error_message, status_code=400):
    # TODO: log error_message
    abort(status_code, description=error_message)


def get_dao(region):
    dao = Dao(region, mongo_client=mongo_client)
    if not dao:
        err('Error connecting to DB (region {})'.format(region))
    return dao


def auth_user(request, dao, check_regions=True, needs_super=False):
    session_id = request.cookies.get('session_id')
    user = dao.get_user_by_session_id_or_none(session_id)
    if not user:
        err("Permission denied", 403)
    if needs_super and user.admin_level != 'SUPER':
        err("Permission denied", 403)
    if user.admin_level == 'REGION' and \
            check_regions and \
            dao.region_id not in user.admin_regions:
        err("Permission denied", 403)
    return user


def is_allowed_origin(origin):
    dragon = r"http(s)?:\/\/(stage\.|www\.)?(notgarpr\.com|192\.168\.[^\.]+\.[^\.]+?|njssbm\.com|garpr\.com)(\:[\d]*)?$"  # noqa
    return re.match(dragon, origin)


def is_user_admin_for_regions(user, regions):
    '''
    returns true is user is an admin for ANY of the regions
    '''
    if user.admin_level == 'SUPER':
        return True
    return any(r in user.admin_regions for r in regions)

# start of URL resources


class RegionListResource(restful.Resource):

    def get(self):
        regions_dict = {'regions': [
            r.dump(context='web') for r in Dao.get_all_regions(mongo_client)]}

        return regions_dict

    def post(self):
        dao = get_dao(None)
        auth_user(request, dao, check_regions=False, needs_super=True)

        parser = reqparse.RequestParser() \
            .add_argument('region_id', type=str) \
            .add_argument('activeTF', type=str) \

        args = parser.parse_args()

        region_id = args['region_id']
        activeTF = args['activeTF'].lower() == 'true'
        
        try:
            dao.update_region_activeTF(region_id, activeTF)
            return 200
        except:
            return 'Error', 400


class PlayerListResource(restful.Resource):

    # returns: match_quality
    # if match_quality > 0, consider it a match
    def _player_matches_query(self, player, query):
        player_name = player.name.lower()
        query = query.lower()

        # try matching the full name first
        if player_name == query:
            return 10

        # split the player name on common dividers and try to match against
        # each part starting from the beginning
        # split on: . | space
        tokens = re.split('\.|\|| ', player_name)
        for token in tokens:
            if token:
                if token.startswith(query):
                    return 5

        # if query is >= 3 chars, allow substring matching
        # this is to allow players with very short names to appear for small
        # search terms
        if len(query) >= 3 and query in player_name:
            return 1

        # no match
        return 0

    def _get_players_matching_query(self, players, query):
        # get list of (player, match_quality)
        matching_players = [(player, self._player_matches_query(player, query)) for player in players]

        # sort by most relevant matches
        matching_players = sorted(
                filter(lambda x: x[1] > 0, matching_players),
                key=lambda x: -x[1])

        # restrict to most relevant matches
        matching_players = matching_players[:TYPEAHEAD_PLAYER_LIMIT]

        # return player objects
        return [p[0] for p in matching_players]

    def get(self, region):
        dao = get_dao(region)

        parser = reqparse.RequestParser() \
            .add_argument('alias', type=str) \
            .add_argument('query', type=str) \
            .add_argument('all', type=bool)

        args = parser.parse_args()

        return_dict = {}
        exclude_properties = ['aliases']

        # single player matching alias within region
        if args['alias']:
            return_dict['players'] = []
            db_player = dao.get_player_by_alias(args['alias'])
            if db_player:
                return_dict['players'].append(db_player.dump(context='web',
                                                             exclude=exclude_properties))
        # search multiple players by name across all regions
        elif args['query']:
            # TODO: none checks on below list comprehensions
            all_players = dao.get_all_players(all_regions=True)
            return_dict['players'] = [p.dump(context='web',
                                             exclude=exclude_properties)
                                      for p in self._get_players_matching_query(all_players, args['query'])]
        # get all players in all regions
        elif args['all']:
            all_players = dao.get_all_players(all_regions=True)
            return_dict['players'] = [p.dump(context='web',
                                             exclude=exclude_properties)
                                      for p in sorted(all_players, key=lambda player: player.name.lower())]
        # all players within region
        else:
            return_dict['players'] = [p.dump(context='web',
                                             exclude=exclude_properties)
                                      for p in sorted(dao.get_all_players(),
                                                      key=lambda player: player.name.lower())]

        return return_dict


class PlayerResource(restful.Resource):

    def get(self, region, id):
        dao = get_dao(region)

        player = None
        try:
            player = dao.get_player_by_id(ObjectId(id))
        except:
            err('Invalid ObjectID')
        if not player:
            err('Player not found')

        return player.dump(context='web')

    def put(self, region, id):
        dao = get_dao(region)
        auth_user(request, dao)

        player = None
        try:
            player = dao.get_player_by_id(ObjectId(id))
        except:
            err('Invalid ObjectID')
        if not player:
            err('No player found with that region/id.')

        parser = reqparse.RequestParser() \
            .add_argument('name', type=str) \
            .add_argument('aliases', type=list) \
            .add_argument('regions', type=list)

        args = parser.parse_args()

        if args['name']:
            player.name = args['name']
        if args['aliases'] is not None:
            for a in args['aliases']:
                if not isinstance(a, unicode):
                    err("Each alias must be a string")
            new_aliases = [a.lower() for a in args['aliases']]
            if player.name.lower() not in new_aliases:
                err("Aliases must contain the players name!")
            player.aliases = new_aliases
        if args['regions'] is not None:
            for a in args['regions']:
                if not isinstance(a, unicode):
                    err("Each region must be a string")
            player.regions = args['regions']

        dao.update_player(player)

        return player.dump(context='web')

class PlayerTournamentResource(restful.Resource):
    def get(self, region, id):
        dao = get_dao(None)

        try:
            tournament_objects = dao.get_all_player_tournaments_by_id(ObjectId(id))
            tournaments = []
            for t in tournament_objects:
                t = t.dump(context='web')
                tournaments.append(t)

            return tournaments
        except Exception as e:
            print e
            return 400

class PlayerSortedTournamentResource(restful.Resource):
    def get(self, region, id):
        dao = get_dao(None)

        try:
            region_sorted_tournament_counts = dao.sort_player_tournaments_by_region(ObjectId(id))
            return region_sorted_tournament_counts
        except Exception as e:
            import traceback
            traceback.print_exc(file=sys.stdout)
            print 'errrrrrrrror'
            print e
            return 400


class TournamentSeedResource(restful.Resource):

    def post(self, region):
        parser = reqparse.RequestParser() \
            .add_argument('type', type=str, location='json') \
            .add_argument('data', type=unicode, location='json') \
            .add_argument('bracket', type=str, location='json')
        args = parser.parse_args()

        if args['data'] is None:
            err("Data required. (TournamentSeedResource.post)")

        the_bytes = bytearray(args['data'], "utf8")

        if the_bytes[0] == 0xef:
            err("Magic numbers! (TournamentSeedResource.post)")

        type = args['type']
        data = args['data']
        pending_tournament = None

        try:

            if type == 'challonge':
                scraper = ChallongeScraper(data)
            else:
                err("Unknown type")
            pending_tournament, raw_file = M.PendingTournament.from_scraper(
                type, scraper, region)
        except Exception as ex:
            err('Scraper encountered an error ' + str(ex))

        if not pending_tournament or not raw_file:
            err('Scraper encountered an error - null')

        pending_tournament_json = pending_tournament.dump(
            context='web', exclude=('date', 'matches', 'regions', 'type'))
        return pending_tournament_json


class TournamentListResource(restful.Resource):

    def get(self, region):
        dao = get_dao(region)

        parser = reqparse.RequestParser() \
            .add_argument('includePending', type=str, default='false')
        args = parser.parse_args()

        if args['includePending'] == 'true':
            auth_user(request, dao)

        tournaments = dao.get_all_tournaments(regions=[region])
        only_properties = ('id',
                           'name',
                           'date',
                           'regions',
                           'excluded')

        # temporary fix
        all_tournament_jsons = []
        for t in tournaments:
            try:
                all_tournament_jsons.append(t.dump(context='web',
                                                   only=only_properties))

            except:
                print 'error inserting tournament', t

        if args['includePending'] == 'true':
            # add a pending field for all existing tournaments
            for t in all_tournament_jsons:
                t['pending'] = False

            pending_tournaments = dao.get_all_pending_tournaments(regions=[region])
            if pending_tournaments:
                for p in pending_tournaments:
                    try:
                        p = p.dump(context='web',
                                   only=only_properties)
                        p['pending'] = True
                        all_tournament_jsons.append(p)
                    except:
                        print 'error inserting pending tournament', p

        return_dict = {}
        return_dict['tournaments'] = all_tournament_jsons

        return return_dict

    def post(self, region):
        dao = get_dao(region)
        auth_user(request, dao)

        parser = reqparse.RequestParser() \
            .add_argument('type', type=str, location='json') \
            .add_argument('data', type=unicode, location='json') \
            .add_argument('bracket', type=str, location='json') \
            .add_argument('included_phases', type=list, location='json')
        args = parser.parse_args()

        if args['data'] is None:
            err("Tournament data required.")

        the_bytes = bytearray(args['data'], "utf8")

        if the_bytes[0] == 0xef:
            print "found magic numbers"
            err("Magic numbers!")

        type = args['type']
        data = args['data']
        included_phases = args['included_phases']
        pending_tournament = None

        try:
            if type == 'tio':
                if args['bracket'] is None:
                    err("Missing bracket name")
                data_bytes = bytes(data)
                if data_bytes[0] == '\xef':
                    data = data[:3]
                scraper = TioScraper(data, args['bracket'])
            elif type == 'challonge':
                scraper = ChallongeScraper(data)
            elif type == 'smashgg':
                scraper = SmashGGScraper(data, included_phases)
            else:
                err("Unknown tournament type")
            pending_tournament, raw_file = M.PendingTournament.from_scraper(
                type, scraper, region)
        except Exception as ex:
            err('Scraper encountered an error: ' + str(ex))

        if not pending_tournament or not raw_file:
            err('Scraper encountered an error.')

        try:
            pending_tournament.alias_to_id_map = alias_service.get_alias_to_id_map_in_list_format(
                dao, pending_tournament.players)
        except:
            err('Alias service encountered an error')

        # If the tournament is too large, don't insert the raw file into the db.
        if len(pending_tournament.players) < 1000:
            try:
                raw_file = dao.insert_raw_file(raw_file)
            except Exception as ex:
                print ex
                err('Dao insert_raw_file encountered an error')
        else:
            print 'Skipping inserting raw file for tournament because it is too large'

        try:
            new_id = dao.insert_pending_tournament(pending_tournament)
            return_dict = {
                'id': str(new_id)
            }
            return return_dict
        except Exception as ex:
            err('Dao insert_pending_tournament encountered an error')

        err('Unknown error!')

# TODO: we shouldn't be doing this, instead we should pass the relevant player/
# match information in different objects


def convert_tournament_to_response(tournament, dao):
    return_dict = tournament.dump(context='web', exclude=('orig_ids',))

    return_dict['players'] = [{
        'id': p,
        'name': dao.get_player_by_id(ObjectId(p)).name
    } for p in return_dict['players']]

    return_dict['matches'] = [{
        'winner_id': m['winner'],
        'loser_id': m['loser'],
        'winner_name': dao.get_player_by_id(ObjectId(m['winner'])).name,
        'loser_name': dao.get_player_by_id(ObjectId(m['loser'])).name,
        'match_id': m['match_id'],
        'excluded': m['excluded']
    } for m in return_dict['matches']]

    return return_dict


class TournamentResource(restful.Resource):

    def get(self, region, id):
        dao = get_dao(region)
        response = None
        tournament = None
        try:
            tournament = dao.get_tournament_by_id(ObjectId(id))
        except:
            err('Invalid ObjectID')
        if tournament is not None:
            response = convert_tournament_to_response(tournament, dao)
        else:
            auth_user(request, dao)

            pending_tournament = dao.get_pending_tournament_by_id(ObjectId(id))
            if not pending_tournament:
                err('Not found!')
            response = pending_tournament.dump(context='web')

        return response

    def put(self, region, id):
        dao = get_dao(region)
        auth_user(request, dao)

        parser = reqparse.RequestParser() \
            .add_argument('name', type=str) \
            .add_argument('date', type=str) \
            .add_argument('players', type=list) \
            .add_argument('matches', type=list) \
            .add_argument('regions', type=list) \
            .add_argument('pending', type=bool)

        args = parser.parse_args()

        tournament = None
        try:
            if args['pending']:
                tournament = dao.get_pending_tournament_by_id(ObjectId(id))
            else:
                tournament = dao.get_tournament_by_id(ObjectId(id))
        except:
            err('Invalid ObjectID')
        if not tournament:
            err("No tournament found with that id.")

        try:
            if args['name']:
                tournament.name = args['name']
            if args['date']:
                try:
                    tournament.date = datetime.strptime(
                        args['date'].strip(), '%m/%d/%y')
                except:
                    err("Invalid date format")
            if args['players']:
                # this should rarely be used (if it is used, players will not
                # unmerge reliably)
                for p in args['players']:
                    if not isinstance(p, unicode):
                        err("each player must be a string")
                tournament.players = [ObjectId(i) for i in args['players']]
                tournament.orig_ids = [pid for pid in tournament.players]
            if args['matches']:
                for d in args['matches']:
                    if not isinstance(d, dict):
                        err("matches must be a dict")
                    if (not isinstance(d['winner'], unicode)) or (
                            not isinstance(d['loser'], unicode)):
                        err("winner and loser must be strings")
                # turn the list of dicts into list of matchresults
                matches = [M.Match(winner=ObjectId(m['winner']), loser=ObjectId(
                    m['loser'])) for m in args['matches']]
                tournament.matches = matches
            if args['regions']:
                for p in args['regions']:
                    if not isinstance(p, unicode):
                        err("each region must be a string")
                tournament.regions = args['regions']
        except:
            err('Invalid ObjectID')

        try:
            if args['pending']:
                dao.update_pending_tournament(tournament)
            else:
                print tournament
                dao.update_tournament(tournament)
        except:
            err('Update Tournament Error')

        if args['pending']:
            return dao.get_pending_tournament_by_id(
                tournament.id).dump(context='web')
        else:
            return convert_tournament_to_response(
                dao.get_tournament_by_id(tournament.id), dao)

    def delete(self, region, id):
        """ Deletes a tournament.
            Route restricted to admins for this region.
            Be VERY careful when using this """
        dao = get_dao(region)
        user = auth_user(request, dao)

        tournament_to_delete = None
        try:
            tournament_to_delete = dao.get_pending_tournament_by_id(
                ObjectId(id))
        except:
            err('Invalid ObjectID')
        if tournament_to_delete:  # its a pending tournament
            if not is_user_admin_for_regions(
                    user, tournament_to_delete.regions):
                err('Permission denied', 403)
            dao.delete_pending_tournament(tournament_to_delete)
        else:  # not a pending tournament, might be a finalized tournament
            tournament_to_delete = dao.get_tournament_by_id(
                ObjectId(id))  # ID must be valid if we got here
            if not tournament_to_delete:  # can't find anything, whoops
                err("No tournament (pending or finalized) found with that id.")
            if not is_user_admin_for_regions(
                    user, tournament_to_delete.regions):
                err('Permission denied')
            dao.delete_tournament(tournament_to_delete)

        return {"success": True}

    def post(self, region, id):
        """
        This post request changes a flag for the indicated tournament
        determining if it is Excluded a tournament from ranking calculation
        """
        dao = get_dao(region)
        auth_user(request, dao)

        parser = reqparse.RequestParser()
        parser.add_argument('excluded_tf', type=str)

        args = parser.parse_args()
        excluded = (args['excluded_tf'].lower() == 'true')

        try:
            dao.set_tournament_exclusion_by_tournament_id(ObjectId(id), excluded)
            return 200
        except:
            return 'Error', 400


class PendingTournamentResource(restful.Resource):
    """
    Currently only updates the alias_to_id_map in the pending tournament
    """

    def put(self, region, id):
        dao = get_dao(region)
        auth_user(request, dao)

        parser = reqparse.RequestParser() \
            .add_argument('name', type=str) \
            .add_argument('players', type=list) \
            .add_argument('matches', type=list) \
            .add_argument('regions', type=list) \
            .add_argument('alias_to_id_map', type=list)

        args = parser.parse_args()

        pending_tournament = None
        try:
            pending_tournament = dao.get_pending_tournament_by_id(ObjectId(id))
        except:
            err('Invalid ObjectID')
        if not pending_tournament:
            err("No pending tournament found with that id.")

        data = {'alias_to_id_map': [M.AliasMapping.load(
            alias_item, context='web') for alias_item in args['alias_to_id_map']]}

        if not data:
            err('Request couldnt be converted to pending tournament')

        try:
            print "Incoming", data["alias_to_id_map"]
            print "DB", pending_tournament.alias_to_id_map
            for alias_item in data["alias_to_id_map"]:
                player_alias = alias_item.player_alias
                player_id = alias_item.player_id
                pending_tournament.set_alias_id_mapping(
                    player_alias, player_id)
        except:
            print 'Error processing alias_to_id map'
            err('Error processing alias_to_id map')

        try:
            dao.update_pending_tournament(pending_tournament)
            return pending_tournament.dump(context='web')
        except:
            err('Encountered an error inserting pending tournament')


class FinalizeTournamentResource(restful.Resource):
    """ Converts a pending tournament to a tournament.
        Works only if the PendingTournament's alias_to_id_map is completely filled out.
        Route restricted to admins for this region. """

    def post(self, region, id):
        print "finalize tournament post"
        dao = get_dao(region)
        pending_tournament = None
        try:
            pending_tournament = dao.get_pending_tournament_by_id(ObjectId(id))
        except:
            err('Invalid ObjectID')
        if not pending_tournament:
            err('No pending tournament found with that id.')
        auth_user(request, dao)

        new_player_names = []
        for mapping in pending_tournament.alias_to_id_map:
            if mapping.player_id is None:
                new_player_names.append(mapping.player_alias)

        for player_name in new_player_names:
            player = M.Player.create_with_default_values(player_name, region)
            player_id = dao.insert_player(player)
            pending_tournament.set_alias_id_mapping(player_name, player_id)

        # validate players in this tournament
        for mapping in pending_tournament.alias_to_id_map:
            try:
                player_id = mapping.player_id
                # TODO: reduce queries to DB by batching
                player = dao.get_player_by_id(player_id)
                if player.merged:
                    err('Player {} has already been merged'.format(player.name))
            except:
                err('Not all player ids are valid')

        try:
            dao.update_pending_tournament(pending_tournament)
            tournament = M.Tournament.from_pending_tournament(
                pending_tournament)
            tournament_id = dao.insert_tournament(tournament)
            dao.delete_pending_tournament(pending_tournament)
            return {"success": True, "tournament_id": str(tournament_id)}
        except ValueError as e:
            print e
            err('Not all player aliases in this pending tournament have been mapped to player ids.')
        except:
            err('Dao threw an error somewhere')


class AddTournamentMatchResource(restful.Resource):

    def get(self, region, id):
        pass

    def put(self, region, id):
        dao = get_dao(region)
        user = auth_user(request, dao)

        parser = reqparse.RequestParser() \
            .add_argument('tournament_id', type=str) \
            .add_argument('winner_id', type=str) \
            .add_argument('loser_id', type=str)

        args = parser.parse_args()
        tournament = dao.get_tournament_by_id(ObjectId(id))

        if not user:
            err('Permission denied', 403)
        if not is_user_admin_for_regions(user, tournament.regions):
            err('Permission denied', 403)

        winner_id = args['winner_id']
        loser_id = args['loser_id']

        if winner_id is None or loser_id is None:
            err("winner and loser IDs not present. Cannot continue")

        try:
            dao.add_match_by_tournament_id(
                ObjectId(id), ObjectId(winner_id), ObjectId(loser_id))
        except Exception as e:
            print 'error adding match to tournament: ' + str(e)
            err('error adding match to tournament: ' + str(e))


class ExcludeTournamentMatchResource(restful.Resource):

    def get(self, region, id):
        pass

    def post(self, region, id):
        dao = get_dao(region)
        user = auth_user(request, dao)

        parser = reqparse.RequestParser() \
            .add_argument('tournament_id', type=str) \
            .add_argument('match_id', type=str) \
            .add_argument('excluded_tf', type=str)

        args = parser.parse_args()
        try:
            tournament = dao.get_tournament_by_id(ObjectId(id))
        except:
            err('Casting error')

        if not is_user_admin_for_regions(user, tournament.regions):
            err('Permission denied', 403)

        match_id = int(args['match_id'])
        excluded = (args['excluded_tf'].lower() == 'true')

        try:
            dao.set_match_exclusion_by_tournament_id_and_match_id(
                ObjectId(id), match_id, excluded)
        except Exception as e:
            print e
            err('Match exclusion failed')


class SwapWinnerLoserMatchResource(restful.Resource):

    def get(self, region):
        pass

    def post(self, region, id):
        dao = get_dao(region)
        user = auth_user(request, dao)

        parser = reqparse.RequestParser() \
            .add_argument('tournament_id', type=str) \
            .add_argument('match_id', type=str)

        args = parser.parse_args()

        tournament_id = args['tournament_id']
        match_id = int(args['match_id'])

        tournament = dao.get_tournament_by_id(ObjectId(tournament_id))

        if not is_user_admin_for_regions(user, tournament.regions):
            err('Permission denied')

        try:
            dao.swap_winner_loser_by_tournament_id_and_match_id(
                ObjectId(tournament_id), match_id)
        except Exception as e:
            err('Swap Winner Loser failed: ' + str(e))


class RankingsResource(restful.Resource):

    def get(self, region):
        dao = get_dao(region)

        return_dict = dao.get_latest_ranking().dump(context='web')
        if not return_dict:
            err('Dao couldnt give us rankings')

        ranking_list = []
        for r in return_dict['ranking']:
            player = dao.get_player_by_id(ObjectId(r['player']))
            if player:
                r['name'] = player.name
                r['id'] = str(r.pop('player'))
                ranking_list.append(r)

        ranking_criteria = dao.get_region_ranking_criteria(region)

        return_dict['ranking'] = ranking_list
        return_dict['ranking_criteria'] = ranking_criteria

        return return_dict

    def put(self, region):
        dao = get_dao(region)
        auth_user(request, dao)

        parser = reqparse.RequestParser() \
            .add_argument('ranking_activity_day_limit', type=str) \
            .add_argument('ranking_num_tourneys_attended', type=str) \
            .add_argument('tournament_qualified_day_limit', type=str)

        args = parser.parse_args()

        try:
            ranking_num_tourneys_attended = int(
                args['ranking_num_tourneys_attended'])
            ranking_activity_day_limit = int(
                args['ranking_activity_day_limit'])
            tournament_qualified_day_limit = int(
                args['tournament_qualified_day_limit'])
        except Exception as e:
            err('Error parsing Ranking Criteria, please try again: ' + str(e))

        print ranking_num_tourneys_attended
        print ranking_activity_day_limit

        try:
            # TODO Update rankings and store criteria in db
            dao.update_region_ranking_criteria(region,
                                               ranking_num_tourneys_attended=ranking_num_tourneys_attended,
                                               ranking_activity_day_limit=ranking_activity_day_limit,
                                               tournament_qualified_day_limit=tournament_qualified_day_limit)
        except Exception as e:
            err('There was an error updating the region rankings criteria:' + str(e))

        return dao.get_region_ranking_criteria(region)

    def post(self, region):
        dao = get_dao(region)
        auth_user(request, dao)

        parser = reqparse.RequestParser() \
            .add_argument('ranking_activity_day_limit', type=str) \
            .add_argument('ranking_num_tourneys_attended', type=str) \
            .add_argument('tournament_qualified_day_limit', type=str)

        args = parser.parse_args()

        # we pass in now so we can mock it out in tests
        now = datetime.now()

        try:
            try:
                ranking_num_tourneys_attended = int(
                    args['ranking_num_tourneys_attended'])
                ranking_activity_day_limit = int(
                    args['ranking_activity_day_limit'])
                tournament_qualified_day_limit = int(
                    args['tournament_qualified_day_limit'])

                # TODO Get stored rankings from the db
                dao.update_region_ranking_criteria(
                    region.lower(),
                    ranking_num_tourneys_attended=ranking_num_tourneys_attended,
                    ranking_activity_day_limit=ranking_activity_day_limit,
                    tournament_qualified_day_limit=tournament_qualified_day_limit)
                print 'Running rankings. day_limit: ' + str(ranking_activity_day_limit) + \
                      ' and num_tourneys: ' + str(ranking_num_tourneys_attended) + \
                      ' and tournament_qualified_day_limit: ' + \
                    str(tournament_qualified_day_limit)

                rankings.generate_ranking(dao, now=now,
                                          day_limit=ranking_activity_day_limit,
                                          num_tourneys=ranking_num_tourneys_attended,
                                          tournament_qualified_day_limit=tournament_qualified_day_limit)
            except:
                rankings.generate_ranking(dao, now=now)
        except Exception as e:
            print str(e)
            err('There was an error updating rankings')

        return self.get(region)


class MatchesResource(restful.Resource):

    def get(self, region, id):
        dao = get_dao(region)

        parser = reqparse.RequestParser() \
            .add_argument('opponent', type=str)

        args = parser.parse_args()
        return_dict = {}

        player = None
        try:
            player = dao.get_player_by_id(ObjectId(id))
        except:
            err('Invalid ObjectID')

        return_dict['player'] = {'id': str(player.id), 'name': player.name}
        player_list = [player]

        opponent_id = args['opponent']
        if opponent_id is not None:
            try:
                opponent = dao.get_player_by_id(ObjectId(args['opponent']))
                return_dict['opponent'] = {
                    'id': str(opponent.id), 'name': opponent.name}
                player_list.append(opponent)
            except:
                err('Invalid ObjectID')

        match_list = []
        return_dict['matches'] = match_list
        return_dict['wins'] = 0
        return_dict['losses'] = 0

        if player.merged:
            # no need to look up tournaments for merged players
            return return_dict

        # hacky solution for now
        region_obj = dao.get_region(region)
        qualifying_tournaments = set()
        now = datetime.now()
        day_limit = region_obj.ranking_activity_day_limit

        tournaments = dao.get_all_tournaments(players=player_list)
        if not tournaments:
            err('No tournaments found')
        for tournament in tournaments:
            for match in tournament.matches:
                if (opponent_id is not None and match.contains_players(player.id, opponent.id)) or \
                        (opponent_id is None and match.contains_player(player.id)):
                    match_dict = {}
                    match_dict['tournament_id'] = str(tournament.id)
                    match_dict['tournament_name'] = tournament.name
                    match_dict[
                        'tournament_date'] = tournament.date.strftime("%x")
                    match_dict['opponent_id'] = str(
                        match.get_opposing_player_id(player.id))
                    try:
                        match_dict['opponent_name'] = dao.get_player_by_id(
                            ObjectId(match_dict['opponent_id'])).name
                    except:
                        err('Invalid ObjectID')

                    if tournament.date >= (now - timedelta(day_limit)):
                        qualifying_tournaments.add(tournament.id)

                    if match.excluded is True:
                        match_dict['result'] = 'excluded'
                    elif match.did_player_win(player.id):
                        match_dict['result'] = 'win'
                        return_dict['wins'] += 1
                    else:
                        match_dict['result'] = 'lose'
                        return_dict['losses'] += 1

                    match_list.append(match_dict)

        return_dict['num_qualifying'] = len(qualifying_tournaments)
        return return_dict


class SmashGGMappingResource(restful.Resource):

    def get(self):
        parser = reqparse.RequestParser() \
            .add_argument('bracket_url', type=str)

        args = parser.parse_args()
        url = args['bracket_url']

        event_name = SmashGGScraper.get_tournament_event_name_from_url(url)
        phase_name = SmashGGScraper.get_tournament_phase_name_from_url(url)
        id_map = SmashGGScraper.get_phasename_id_map(event_name, phase_name)
        return id_map


class MergeListResource(restful.Resource):

    def get(self, region):
        dao = get_dao(region)
        auth_user(request, dao)

        merges = dao.get_all_merges()
        merges.sort(key=lambda m: m.time, reverse=True)

        return_dict = {}
        merges = dao.get_all_merges()
        return_dict['merges'] = [m.dump(context='web')
                                 for m in merges]

        for merge, merge_dump in zip(merges, return_dict['merges']):
            # TODO: store names in merge object
            source_player = dao.get_player_by_id(merge.source_player_obj_id)
            target_player = dao.get_player_by_id(merge.target_player_obj_id)

            if source_player is not None and target_player is not None:
                merge_dump['source_player_name'] = source_player.name
                merge_dump['target_player_name'] = target_player.name

        return return_dict

    def put(self, region):
        dao = get_dao(region)
        user = auth_user(request, dao)

        parser = reqparse.RequestParser() \
            .add_argument('source_player_id', type=str) \
            .add_argument('target_player_id', type=str)

        args = parser.parse_args()
        try:
            print args
            source_player_id = ObjectId(args['source_player_id'])
            target_player_id = ObjectId(args['target_player_id'])
        except:
            err('invalid ids')
        # the above should validate that we have real objectIDs
        # now lets validate that both of those players exist
        player1 = dao.get_player_by_id(source_player_id)
        player2 = dao.get_player_by_id(target_player_id)

        if not player1:
            err('source_player not found')
        if not player2:
            err('target_player not found')
        if not is_user_admin_for_regions(user, player1.regions):
            err('Permission denied', 403)
        if not is_user_admin_for_regions(user, player2.regions):
            err('Permission denied', 403)

        # get curr time
        now = datetime.now()
        the_merge = M.Merge(requester_user_id=user.id,
                            source_player_obj_id=source_player_id,
                            target_player_obj_id=target_player_id,
                            time=now,
                            id=ObjectId())
        try:
            dao.insert_merge(the_merge)
            return_dict = {'status': "success", 'id': str(the_merge.id)}
            return return_dict, 200
        except Exception as e:
            err('error merging players: ' + str(e))


class MergeResource(restful.Resource):

    def get(self, region, id):
        # TODO: decide if we want this
        pass

    def delete(self, region, id):
        dao = get_dao(region)
        auth_user(request, dao)

        try:
            merge_id = ObjectId(id)
        except:
            err('invalid ids')

        try:
            the_merge = dao.get_merge(merge_id)
            dao.undo_merge(the_merge)
        except Exception as e:
            err('error merging players: ' + str(e))


class SessionResource(restful.Resource):

    def put(self):
        dao = get_dao(None)

        parser = reqparse.RequestParser() \
            .add_argument('username', type=str) \
            .add_argument('password', type=str)

        args = parser.parse_args()

        session_id = dao.check_creds_and_get_session_id_or_none(
            args['username'], args['password'])
        if not session_id:
            err('Permission denied', 403)
        resp = jsonify({"status": "connected"})
        resp.set_cookie('session_id', session_id)
        return resp

    ''' logout, destroys session_id mapping on client and server side '''

    def delete(self):
        dao = get_dao(None)

        parser = reqparse.RequestParser() \
            .add_argument('session_id', location='cookies', type=str)

        args = parser.parse_args()
        logout_success = dao.logout_user_or_none(args['session_id'])
        if not logout_success:
            err('who is you')
        return ('logout success', 200,
                {'Set-Cookie': "session_id=deleted; expires=Thu, 01 Jan 1970 00:00:00 GMT"})

    def get(self):
        dao = get_dao(None)
        user = auth_user(request, dao, check_regions=False)
        return_dict = user.dump(
            context='web', exclude=('salt', 'hashed_password'))

        return return_dict


class UserResource(restful.Resource):
    def put(self):
        dao = get_dao(None)
        user = auth_user(request, dao, check_regions=False)

        parser = reqparse.RequestParser()
        parser.add_argument('old_pass', location='json', type=str)
        parser.add_argument('new_pass', location='json', type=str)

        args = parser.parse_args()
        old_pass = args['old_pass']
        new_pass = args['new_pass']

        try:
            if dao.check_creds(user.username, old_pass):
                dao.change_passwd(user.username, new_pass)
                return 200
            else:
                err('Bad password')
        except Exception as ex:
            print ex
            err('Password change not successful')


class AdminFunctionsResource(restful.Resource):

    def get(self):
        pass

    def put(self):
        dao = get_dao(None)
        auth_user(request, dao, check_regions=False, needs_super=True)


        parser = reqparse.RequestParser() \
            .add_argument('function_type', location='json', type=str) \
            .add_argument('new_region', location='json', type=str) \
            .add_argument('new_user_name', location='json', type=str) \
            .add_argument('new_user_pass', location='json', type=str) \
            .add_argument('new_user_permissions', location='json', type=str) \
            .add_argument('new_user_regions', location='json', type=list)
        args = parser.parse_args()

        function_type = args['function_type']
        if function_type == 'region':
            region_name = args['new_region']

            # Execute region addition
            if dao.create_region(region_name):
                print("region created:" + region_name)

        elif function_type == 'user':
            uname = args['new_user_name']
            upass = args['new_user_pass']
            uperm = args['new_user_permissions']
            uregions = args['new_user_regions']

            if uperm not in M.ADMIN_LEVEL_CHOICES:
                err('Invalid permission selection!')

            # Execute user addition
            dao = Dao(None, mongo_client)
            try:
                dao.create_user(uname, upass, uregions, uperm)
                print("user created:" + uname)
            except Exception as e:
                print e
                err('Error creating user!')


@api.representation('text/plain')
class LoaderIOTokenResource(restful.Resource):

    def get(self):
        return Response(config.get_loaderio_token())


@app.after_request
def add_security_headers(resp):
    resp.headers[
        'Strict-Transport-Security'] = "max-age=31536000; includeSubdomains"
    resp.headers[
        'Content-Security-Policy'] = "default-src https: data: 'unsafe-inline' 'unsafe-eval'"
    resp.headers['X-Frame-Options'] = "DENY"
    resp.headers['X-XSS-Protection'] = "1; mode=block"
    resp.headers['X-Content-Type-Options'] = "nosniff"
    return resp


@app.after_request
def add_cors(resp):
    """ Ensure all responses have the CORS headers. This ensures any failures are also accessible
        by the client. """
    the_origin = request.headers.get('Origin', '*')
    if not is_allowed_origin(the_origin):
        return resp
    resp.headers['Access-Control-Allow-Origin'] = the_origin
    resp.headers['Access-Control-Allow-Credentials'] = 'true'
    resp.headers[
        'Access-Control-Allow-Methods'] = 'POST, OPTIONS, GET, PUT, DELETE'
    resp.headers['Access-Control-Allow-Headers'] = request.headers.get(
        'Access-Control-Request-Headers', 'Authorization')
    resp.headers["Access-Control-Expose-Headers"] = "Set-Cookie"
    # set low for debugging
    if app.debug:
        resp.headers['Access-Control-Max-Age'] = '1'
    return resp


api.add_resource(MatchesResource, '/<string:region>/matches/<string:id>')

api.add_resource(MergeResource, '/<string:region>/merges/<string:id>')
api.add_resource(MergeListResource, '/<string:region>/merges')

api.add_resource(RegionListResource, '/regions')

api.add_resource(PlayerListResource, '/<string:region>/players')
api.add_resource(PlayerResource, '/<string:region>/players/<string:id>')
api.add_resource(PlayerTournamentResource, '/<string:region>/players/<string:id>/tournaments')
api.add_resource(PlayerSortedTournamentResource, '/<string:region>/players/<string:id>/sortedtournaments')

api.add_resource(TournamentSeedResource, '/<string:region>/tournamentseed')

api.add_resource(TournamentListResource, '/<string:region>/tournaments')
api.add_resource(TournamentResource,
                 '/<string:region>/tournaments/<string:id>')
api.add_resource(PendingTournamentResource,
                 '/<string:region>/pending_tournaments/<string:id>')
api.add_resource(FinalizeTournamentResource,
                 '/<string:region>/tournaments/<string:id>/finalize')

api.add_resource(ExcludeTournamentMatchResource,
                 '/<string:region>/tournaments/<string:id>/excludeMatch')
api.add_resource(SwapWinnerLoserMatchResource,
                 '/<string:region>/tournaments/<string:id>/swapWinnerLoser')
api.add_resource(AddTournamentMatchResource,
                 '/<string:region>/tournaments/<string:id>/addMatch')

api.add_resource(SmashGGMappingResource, '/smashGgMap')

api.add_resource(RankingsResource, '/<string:region>/rankings')

api.add_resource(SessionResource, '/users/session')

api.add_resource(UserResource, '/user')

api.add_resource(LoaderIOTokenResource,
                 '/{}/'.format(config.get_loaderio_token()))

api.add_resource(AdminFunctionsResource, '/adminfunctions')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(
        sys.argv[1]), debug=(sys.argv[2] == 'True'))
