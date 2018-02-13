angular.module('app.common').service('RegionService', function ($http, PlayerService, TournamentService, RankingsService, MergeService, SessionService) {
    var service = {
        regionsPromise: $http.get(hostname + 'regions'),
        regions: [],
        display_regions: [],
        region: '',
        setRegion: function (newRegionId) {
            if (!this.region || newRegionId != this.region.id) {
                this.regionsPromise.then(function(response) {
                    service.region = service.getRegionFromRegionId(newRegionId);
                    PlayerService.playerList = [];
                    TournamentService.tournamentList = [];
                    RankingsService.rankingsList = [];
                    RankingsService.rankingsTournaments = [];
                    MergeService.mergeList = [];
                    service.populateDataForCurrentRegion();
                });
            }
        },
        getRegionFromRegionId: function(regionId) {
            return this.regions.filter(function(element) {
                return element.id == regionId;
            })[0];
        },
        getRegionDisplayNameFromRegionId: function(regionId) {
            var region = this.getRegionFromRegionId(regionId);
            if(region!=null){
                return region.display_name;
            }else{
                return "Invalid Region";
            }
        },
        populateDataForCurrentRegion: function() {
            $http.get(hostname + this.region.id + '/players').
                success(function(data) {
                    PlayerService.playerList = data;
                });

            $http.get(hostname + this.region.id + '/rankings').
                success(function(data) {
                    RankingsService.rankingsList = data;
                    RankingsService.rankingsTournamentsIds = data.tournaments;
                    RankingsService.rankingsTournaments = 
                        TournamentService.getTournamentsByIds(RankingsService.rankingsTournamentsIds);
                });

            this.populateLoggedInDataForCurrentRegion();
        },
        populateLoggedInDataForCurrentRegion: function() {
            var tournamentURL = '/tournaments';
            if(SessionService.loggedIn) {
                tournamentURL += '?includePending=true';
            }
            SessionService.authenticatedGet(hostname + this.region.id + tournamentURL,
                function(data) {
                    TournamentService.tournamentList = data.tournaments.reverse();
                    TournamentService.tournamentList.forEach(function(tournament){
                        if(tournament.excluded == true)
                            TournamentService.excludedList.push(tournament);
                    })
                    RankingsService.rankingsTournaments = 
                        TournamentService.getTournamentsByIds(RankingsService.rankingsTournamentsIds);
                });

            if(SessionService.loggedIn) {
                SessionService.authenticatedGet(hostname + this.region.id + '/merges',
                    function(data) {
                        MergeService.mergeList = data;
                    });
            } else {
                MergeService.mergeList = null;
            }
        },
        setTournamentExcluded: function(id, excludedTF){
            var i = _.findLastIndex(TournamentService.tournamentList, {id: id});
            if(i >= 0){
                var tournament = TournamentService.tournamentList[i];
                tournament.excluded = excludedTF;
                TournamentService.tournamentList[i] = tournament;
            }
        },
        updateRegionDropdown: function(){
            service.regionsPromise.success(function(data) {
                service.regions = data.regions;

                service.display_regions = [];
                //SET THE REGION DROPDOWN BASED ON ACTIVE FLAG
                data.regions.forEach(region => {
                    if(region.activeTF)
                        service.display_regions.push(region);

                })
            });
        }
    };

    service.updateRegionDropdown();

    /*
    service.display_regions = [{"id": "newjersey", "display_name": "New Jersey"}, // TODO: get this from server
                               {"id": "nyc", "display_name": "NYC Metro Area"},
                               {"id": "li", "display_name": "Long Island"},
                               {"id": "newengland", "display_name": "New England"},
                               {"id": "chicago", "display_name": "Chicago"},
                               {"id": "socal", "display_name": "SoCal"},
                               {"id": "arizona", "display_name": "Arizona"},
                               {"id": "georgia", "display_name": "Georgia"},
                               {"id": "northcarolina", "display_name": "North Carolina"},
                               {"id": "cfl", "display_name": "Central Florida"},
                               {"id": "alabama", "display_name": "Alabama"},
                               {"id": "tennessee", "display_name": "Tennessee"},
                               {"id": "philadelphia", "display_name": "Philadelphia"},
                               {"id": "oregon", "display_name": "Oregon"},
                               {"id": "southcarolina", "display_name": "South Carolina"},
                               {"id": "orangecounty", "display_name": "Orange County"},
                               {"id": "southernvirginia", "display_name": "SoVa"},
                               {"id": "blackhills", "display_name": "Black Hills (South Dakota)"}
                               ];
                               */
    return service;
});
