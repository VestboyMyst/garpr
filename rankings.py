from bson.objectid import ObjectId
from datetime import datetime, timedelta

import trueskill

import logging

import model
import rating_calculators

import sys, traceback
import logging

logger = logging.getLogger('garpr')
logger.info('rankings.py loaded')


def generate_ranking(dao, now=datetime.now(), day_limit=60, num_tourneys=2, tournament_qualified_day_limit=999):
    try:
        logger.info('Beginning ranking calculation for ' + str(dao.region_id))

        player_date_map = {}
        player_id_to_player_map = {}
        ranking_tournaments = []

        tournament_qualified_date = (now - timedelta(days=tournament_qualified_day_limit))
        print('Qualified Date: ' + str(tournament_qualified_date))
        logger.info('Qualified Date: ' + str(tournament_qualified_date))

        tournaments = dao.get_all_tournaments(regions=[dao.region_id])
        for tournament in tournaments:
            if tournament.excluded is True:
                print 'Tournament Excluded:'
                print 'Excluded - ' + str(tournament.name)
                logger.warning('Tournament Excluded: ' + str(tournament.name))
                continue

            if tournament_qualified_date <= tournament.date:
                ranking_tournaments.append(tournament)

                print 'Processing:', tournament.name.encode('utf-8'), str(tournament.date)
                logger.info('Processing: ' + tournament.name.encode('utf-8') + ", " + str(tournament.date))
                for player_id in tournament.players:
                    player_date_map[player_id] = tournament.date

                # TODO add a default rating entry when we add it to the map
                for match in tournament.matches:
                    if match.excluded is True:
                        print('match excluded:')
                        print('Tournament: ' + str(tournament.name))
                        print(str(match))
                        logger.warning('Match excluded: ' + str(match) + ' Tournament: ' + str(tournament.name))
                        continue

                    logger.debug('Getting winner and loser')

                    # don't count matches where either player is OOR
                    winner = dao.get_player_by_id(match.winner)
                    logger.debug('Winner: ' + str(winner))
                    if winner is None:
                        logger.warning('Player found as NoneType. Skipping match')
                        continue
                    elif dao.region_id not in winner.regions:
                        continue

                    loser = dao.get_player_by_id(match.loser)
                    logger.debug('Loser: ' + str(loser))
                    if loser is None:
                        logger.warning('Player found as NoneType. Skipping match')
                        continue
                    elif dao.region_id not in loser.regions:
                        continue

                    if match.winner not in player_id_to_player_map:
                        db_player = dao.get_player_by_id(match.winner)
                        db_player.ratings[dao.region_id] = model.Rating()
                        player_id_to_player_map[match.winner] = db_player

                    if match.loser not in player_id_to_player_map:
                        db_player = dao.get_player_by_id(match.loser)
                        db_player.ratings[dao.region_id] = model.Rating()
                        player_id_to_player_map[match.loser] = db_player

                    winner = player_id_to_player_map[match.winner]
                    loser = player_id_to_player_map[match.loser]

                    rating_calculators.update_trueskill_ratings(
                        dao.region_id, winner=winner, loser=loser)
            else:
                logger.info('Tournament ' + str(tournament.name) + ' outside qualified date. Skipping.')

        print 'Checking for player inactivity...'
        logger.info('Checking for player inactivity...')
        rank = 1
        players = player_id_to_player_map.values()
        sorted_players = sorted(
            players,
            key=lambda player: trueskill.expose(player.ratings[dao.region_id].trueskill_rating()), reverse=True)
        ranking = []
        for player in sorted_players:
            if player is None: 
                logger.warning('NoneType player found while checking inactivity. Skipping.')
                continue

            player_last_active_date = player_date_map.get(player.id)
            if player_last_active_date is None or \
                    dao.is_inactive(player, now, day_limit, num_tourneys) or \
                    dao.region_id not in player.regions:
                logger.debug('Player ' + player.name + ' outside of ranking criteria. Skipping.')
                pass  # do nothing, skip this player
            else:
                logger.debug('Player ' + player.name + ' updating.')
                ranking.append(model.RankingEntry(
                    rank=rank,
                    player=player.id, rating=trueskill.expose(player.ratings[dao.region_id].trueskill_rating())))
                rank += 1

        print 'Updating players...'
        logger.info('Updating players...')
        for i, p in enumerate(players, start=1):
            if p is None: 
                logger.warning('NoneType player found while updating. Skipping.')
                continue
            logger.debug('Updating player ' + p.name)
            dao.update_player(p)
            # TODO: log somewhere later
            # print 'Updated player %d of %d' % (i, len(players))

        print 'Inserting new ranking...'
        logger.info('Inserting new ranking...')
        dao.insert_ranking(model.Ranking(
            id=ObjectId(),
            region=dao.region_id,
            time=now,
            tournaments=[t.id for t in ranking_tournaments],
            ranking=ranking))

        print 'Done!'
        logger.info('Done!')
    except Exception as e:
        print str(e)
        logger.error(str(e))
        tb = traceback.format_exc()
        logging.error(tb)
