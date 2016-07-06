var app = angular.module('myApp', ['ngRoute', 'ui.bootstrap', 'angulartics', 'angulartics.google.analytics', 'facebook']);

app.directive('onReadFile', function ($parse) {
    return {
        restrict: 'A',
        scope: false,
        link: function(scope, element, attrs) {
            var fn = $parse(attrs.onReadFile);

            element.on('change', function(onChangeEvent) {
                var reader = new FileReader();

                reader.onload = function(onLoadEvent) {
                    scope.$apply(function() {
                        fn(scope, {$fileContent:onLoadEvent.target.result});
                    });
                };

                reader.readAsText((onChangeEvent.srcElement || onChangeEvent.target).files[0]);
            });
        }
    };
});

app.service('RegionService', function ($http, PlayerService, TournamentService, RankingsService, MergeService, SessionService) {
    var service = {
        regionsPromise: $http.get(hostname + 'regions'),
        regions: [],
        region: '',
        setRegion: function (newRegionId) {
            if (!this.region || newRegionId != this.region.id) {
                this.regionsPromise.then(function(response) {
                    service.region = service.getRegionFromRegionId(newRegionId);
                    PlayerService.playerList = null;
                    TournamentService.tournamentList = null;
                    RankingsService.rankingsList = null;
                    MergeService.mergeList = null;
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
            return this.regions.filter(function(element) {
                return element.id == regionId;
            })[0].display_name;
        },
        populateDataForCurrentRegion: function() {
            $http.get(hostname + this.region.id + '/players').
                success(function(data) {
                    PlayerService.playerList = data;
                });

            SessionService.authenticatedGet(hostname + this.region.id + '/tournaments?includePending=true',
                function(data) {
                    TournamentService.tournamentList = data.tournaments.reverse();
                });

            $http.get(hostname + this.region.id + '/rankings').
                success(function(data) {
                    RankingsService.rankingsList = data;
                });

            SessionService.authenticatedGet(hostname + this.region.id + '/merges',
                function(data) {
                    console.log("success merges!");
                    console.log(data);
                    MergeService.mergeList = data;
                });
        }
    };

    service.regionsPromise.success(function(data) {
        service.regions = data.regions;
    });
    // only allow New Jersey to show in UI
    service.display_regions = [{"id": "newjersey", "display_name": "New Jersey"}];

    return service;
});

app.service('PlayerService', function($http) {
    var service = {
        playerList: null,
        getPlayerIdFromName: function (name) {
            for (i = 0; i < this.playerList.players.length; i++) {
                p = this.playerList.players[i]
                if (p.name == name) {
                    return p.id;
                }
            }
            return null;
        },
        getPlayerListFromQuery: function(query, filter_fn) {
            url = hostname + defaultRegion + '/players';
            params = {
                params: {
                    query: query
                }
            }

            return $http.get(url, params).then(function(response) {
                players = response.data.players;
                if (filter_fn != undefined) {
                    filtered_players = []
                    for (var i = 0; i < players.length; i++) {
                        if (filter_fn(players[i])) {
                            filtered_players.push(players[i])
                        }
                    }
                    players = filtered_players;
                }
                return players;
            });
        }
    };
    return service;
});

app.service('MergeService', function($http) {
    var service = {
        mergeList: null
    };
    return service;
});

app.service('TournamentService', function() {
    var service = {
        tournamentList: null
    };
    return service;
});

app.service('RankingsService', function() {
    var service = {
        rankingsList: null
    };
    return service;
});

app.service('SessionService', function($http) {
    var service ={
        loggedIn: false,
        userInfo: null,
        authenticatedGet: function(url, successCallback) {
            config = {
                "headers": {
                    "withCredentials": true,
                    "Access-Control-Allow-Credentials": true
                }
            };
            $http.get(url, config).success(successCallback)
        },
        authenticatedPost: function(url, data, successCallback, failureCallback) {
            config = {
                "headers": {
                    "withCredentials": true,
                    "Access-Control-Allow-Credentials": true
                }
            };
            $http.post(url, data, config).success(successCallback).error(failureCallback);
        },
        authenticatedPut: function(url, data, successCallback, failureCallback) {
            if (data === undefined) {
                data = {};
            }
            config = {
                "headers": {
                    "withCredentials": true,
                    "Access-Control-Allow-Credentials": true
                }
            };
            if (failureCallback === undefined) {
                failureCallback = function(data) {}
            }
            $http.put(url, data, config).success(successCallback).error(failureCallback);
        },
        authenticatedDelete: function(url, successCallback) {
            config = {
                "headers": {
                    "withCredentials": true,
                    "Access-Control-Allow-Credentials": true
                }
            };
            $http.delete(url, config).success(successCallback);
        },
        isAdmin: function() {
            if (!this.loggedIn) {
                return false;
            }
            else {
                return this.userInfo.admin_regions.length > 0
            }
        },
        isAdminForRegion: function(regionId) {
            if (!this.loggedIn) {
                return false;
            }
            else {
                return this.userInfo.admin_regions.indexOf(regionId) > -1;
            }
        },
        getAdminRegions: function() {
            return this.userInfo.admin_regions
        }
    };

    return service;
});

app.config(function ($httpProvider) {
    $httpProvider.defaults.withCredentials = true;
    $httpProvider.defaults.useXDomain = true;
    $httpProvider.defaults.headers.common = 'Content-Type: application/json';
    delete $httpProvider.defaults.headers.common['X-Requested-With'];
    //rest of route code
});

app.config(['$routeProvider', function($routeProvider) {
    $routeProvider.when('/:region/rankings', {
        templateUrl: 'rankings.html',
        controller: 'RankingsController',
        activeTab: 'rankings'
    }).
    when('/:region/players', {
        templateUrl: 'players.html',
        controller: 'PlayersController',
        activeTab: 'players'
    }).
    when('/:region/players/:playerId', {
        templateUrl: 'player_detail.html',
        controller: 'PlayerDetailController',
        activeTab: 'players'
    }).
    when('/:region/tournaments', {
        templateUrl: 'tournaments.html',
        controller: 'TournamentsController',
        activeTab: 'tournaments'
    }).
    when('/:region/tournaments/:tournamentId', {
        templateUrl: 'tournament_detail.html',
        controller: 'TournamentDetailController',
        activeTab: 'tournaments'
    }).
    when('/:region/merges', {
        templateUrl: 'merges.html',
        controller: 'MergesController',
        activeTab: 'tournaments'
    }).
    when('/:region/headtohead', {
        templateUrl: 'headtohead.html',
        controller: 'HeadToHeadController',
        activeTab: 'headtohead'
    }).
    when('/about', {
        templateUrl: 'about.html',
        activeTab: 'about'
    }).
    otherwise({
        redirectTo: '/' + defaultRegion + '/rankings'
    });
}]);

app.controller("AuthenticationController", function($scope, $modal, Facebook, SessionService, RegionService) {
    $scope.sessionService = SessionService;
    $scope.regionService = RegionService;
    $scope.postParams = {};
    $scope.errorTxt = "";

    $scope.handleAuthResponse = function(response, status, headers, bleh) {
        console.log(response)
        if (response.status == 'connected') {
            $scope.errorTxt = "";
            $scope.getSessionInfo(function() {
                $scope.closeLoginModal();
            });
        }
        else {
            $scope.sessionService.loggedIn = false;
            $scope.sessionService.userInfo = null;
            $scope.errorTxt = "Login Failed";
        }
    };

    $scope.getSessionInfo = function(callback) {
        $scope.sessionService.authenticatedGet(hostname + 'users/session',
            function(data) {
                console.log("session data")
                console.log(data)
                $scope.sessionService.loggedIn = true;
                $scope.sessionService.userInfo = data;
                $scope.regionService.populateDataForCurrentRegion();
                if (callback) { callback(); }
            }
        );
    }

    $scope.closeLoginModal = function() {
        $scope.modalInstance.close()
    };

    $scope.openLoginModal = function() {
        $scope.modalInstance = $modal.open({
            templateUrl: 'login_modal.html',
            scope: $scope,
            size: 'lg'
        });
    };

    $scope.login = function() {
        console.log("logging in user")
        console.log($scope.postParams)
        url = hostname + 'users/session'
        $scope.sessionService.authenticatedPut(url, $scope.postParams, $scope.handleAuthResponse, $scope.handleAuthResponse);
    };

    $scope.logout = function() {
        console.log("logging out user")
        url = hostname + 'users/session'
        $scope.sessionService.authenticatedDelete(url, $scope.handleAuthResponse, $scope.postParams,
            $scope.handleAuthResponse);
    };

    // Initial login
    $scope.getSessionInfo();
});

app.controller("NavbarController", function($scope, $route, $location, RegionService, PlayerService) {
    $scope.regionService = RegionService;
    $scope.playerService = PlayerService;
    $scope.$route = $route;

    $scope.selectedPlayer = null;

    $scope.playerSelected = function($item) {
        $location.path($scope.regionService.region.id + '/players/' + $item.id);
        $scope.selectedPlayer = null;
    };
});

app.controller("RankingsController", function($scope, $routeParams, $modal, RegionService, RankingsService, SessionService) {
    RegionService.setRegion($routeParams.region);
    $scope.regionService = RegionService;
    $scope.rankingsService = RankingsService
    $scope.sessionService = SessionService

    $scope.modalInstance = null;
    $scope.disableButtons = false;

    $scope.prompt = function() {
        $scope.modalInstance = $modal.open({
            templateUrl: 'generate_rankings_prompt_modal.html',
            scope: $scope,
            size: 'lg'
        });
    };

    $scope.confirm = function() {
        $scope.disableButtons = true;
        url = hostname + $routeParams.region + '/rankings';
        successCallback = function(data) {
            $scope.rankingsService.rankingsList = data;
            $scope.modalInstance.close();
        };

        $scope.sessionService.authenticatedPost(url, {}, successCallback, angular.noop);
    };

    $scope.cancel = function() {
        $scope.modalInstance.close();
    };
});

app.controller("TournamentsController", function($scope, $routeParams, $modal, RegionService, TournamentService, SessionService) {
    RegionService.setRegion($routeParams.region);
    $scope.regionService = RegionService;
    $scope.tournamentService = TournamentService;
    $scope.sessionService = SessionService;

    $scope.modalInstance = null;
    $scope.disableButtons = false;
    $scope.errorMessage = false;

    $scope.postParams = {};

    $scope.open = function() {
        $scope.disableButtons = false;
        $scope.modalInstance = $modal.open({
            templateUrl: 'import_tournament_modal.html',
            scope: $scope,
            size: 'lg'
        });
    };

    $scope.setBracketType = function(bracketType) {
        $scope.postParams = {};
        $scope.postParams.type = bracketType;
        $scope.errorMessage = false;
    };

    $scope.close = function() {
        $scope.modalInstance.close();
    };

    $scope.submit = function() {
        console.log($scope.postParams);
        $scope.disableButtons = true;

        url = hostname + $routeParams.region + '/tournaments';
        successCallback = function(data) {
            // TODO don't need to populate everything, just tournaments
            $scope.regionService.populateDataForCurrentRegion()
            $scope.close();
        };

        failureCallback = function(data) {
            $scope.disableButtons = false;
            $scope.errorMessage = true;
        };

        $scope.sessionService.authenticatedPost(url, $scope.postParams, successCallback, failureCallback);
    };

    $scope.loadFile = function(fileContents) {
        $scope.postParams.data = fileContents;
    };

    $scope.openDeleteTournamentModal = function(tournamentId) {
        $scope.modalInstance = $modal.open({
            templateUrl: 'delete_tournament_modal.html',
            scope: $scope,
            size: 'lg'
        });
    $scope.tournamentId = tournamentId;
    };

    $scope.deleteTournament = function() {
        url = hostname + $routeParams.region + '/tournaments/' + $scope.tournamentId;
        successCallback = function(data) {
            window.location.reload();
        };
        $scope.sessionService.authenticatedDelete(url, successCallback);
    };

});

app.controller("TournamentDetailController", function($scope, $routeParams, $http, $modal, RegionService, SessionService, PlayerService) {
    RegionService.setRegion($routeParams.region);
    $scope.regionService = RegionService;
    $scope.sessionService = SessionService;
    $scope.playerService = PlayerService;

    $scope.modalInstance = null;
    $scope.disableButtons = false;
    $scope.errorMessage = false;

    $scope.tournament = null;
    $scope.tournamentId = $routeParams.tournamentId
    $scope.isPendingTournament = false;
    $scope.playerData = {}
    $scope.playerCheckboxState = {};

    $scope.openDetailsModal = function() {
        $scope.modalInstance = $modal.open({
            templateUrl: 'tournament_details_modal.html',
            scope: $scope,
            size: 'lg'
        });
        $scope.postParams = {name: $scope.tournament.name,
                             date: $scope.tournament.date,
                             pending: $scope.isPendingTournament};
        $scope.tournamentRegionCheckbox = {};

        $scope.sessionService.getAdminRegions().forEach(
            function(regionId){
                if($scope.isTournamentInRegion(regionId)){
                    $scope.tournamentRegionCheckbox[regionId] = "IN_REGION";
                }else{
                    $scope.tournamentRegionCheckbox[regionId] = "NOT_IN_REGION";
                }
            });

        $scope.disableButtons = false;
        $scope.errorMessage = false;
    };

    $scope.closeDetailsModal = function() {
        $scope.modalInstance.close()
    };

    $scope.updateTournamentDetails = function() {
        url = hostname + $routeParams.region + '/tournaments/' + $scope.tournamentId;
        $scope.disableButtons = true;

        tournamentInRegion = function(regionId){
            return $scope.tournamentRegionCheckbox[regionId]!=="NOT_IN_REGION";
        };

        $scope.postParams['regions'] = $scope.sessionService.getAdminRegions().filter(tournamentInRegion);

        successCallback = function(data) {
            $scope.tournament = data;
            $scope.closeDetailsModal();
        };

        failureCallback = function(data) {
            $scope.disableButtons = false;
            $scope.errorMessage = true;
        };

        $scope.sessionService.authenticatedPut(url, $scope.postParams, successCallback, failureCallback);

        return;
    };

    $scope.openSubmitPendingTournamentModal = function() {
        $scope.modalInstance = $modal.open({
            templateUrl: 'submit_pending_tournament_confirmation_modal.html',
            scope: $scope,
            size: 'lg'
        });
        $scope.tournamentRegionCheckbox = {};
    };

    $scope.closeSubmitPendingTournamentModal = function() {
        $scope.modalInstance.close()
    };

    $scope.submitPendingTournament = function() {
        url = hostname + $routeParams.region + '/tournaments/' + $scope.tournamentId + '/finalize';
        successCallback = function(data) {
            window.location.reload();
        };
        $scope.sessionService.authenticatedPost(url, {}, successCallback);
    };

    $scope.isTournamentInRegion = function(regionId) {
        return $scope.tournament.regions.indexOf(regionId) > -1
    };

    $scope.onPlayerCheckboxChange = function(playerAlias) {
        $scope.put_tournament_from_ui()
    };

    $scope.playerSelected = function(playerAlias, $item) {
        $scope.put_tournament_from_ui()
    };

    $scope.prettyPrintRegionListForPlayer = function(player) {
        var retString = 'None';
        if (player != null && player.hasOwnProperty('regions')) {
            var regions = player.regions;
            for (i = 0; i < regions.length; i++) {
                r = regions[i];
                if (retString == 'None') {
                    retString = $scope.regionService.getRegionDisplayNameFromRegionId(r);
                }
                else {
                    retString += ', ' + $scope.regionService.getRegionDisplayNameFromRegionId(r);
                }
            }
        }

        return retString
    };

    $scope.update_alias_map_from_ui = function() {
        var alias_map = {}
        for (var player in $scope.playerCheckboxState) {
            if ($scope.playerCheckboxState[player] === true) {
                alias_map[player] = null;
                delete $scope.playerData[player];
            }
        }
        for (var player in $scope.playerData){
            alias_map[player] = $scope.playerData[player].id
        }
        $scope.tournament.alias_to_id_map = alias_map;
    };

    $scope.put_tournament_from_ui = function() {
        $scope.update_alias_map_from_ui()
        console.log($scope.tournament.alias_to_id_map);
        url = hostname + $routeParams.region + '/pending_tournaments/' + $scope.tournamentId;
        $scope.sessionService.authenticatedPut(url, $scope.tournament, $scope.updateData);
    }

    $scope.updateData = function(data) {
        console.log(data)
        $scope.tournament = data;
        if ($scope.tournament.hasOwnProperty('alias_to_id_map')) {
            $scope.isPendingTournament = true;

            // load individual player detail
            for (var player in $scope.tournament.alias_to_id_map) {
                var id = $scope.tournament.alias_to_id_map[player];
                if (id != null) {
                    $scope.playerCheckboxState[player] = false;
                    (function(clsplayer, clsid) {
                        $http.get(hostname + $routeParams.region + '/players/' + clsid).
                            success(function(data) {
                                $scope.playerData[clsplayer] = data;
                            })
                    })(player, id);
                }
                else {
                    $scope.playerCheckboxState[player] = true;
                }
            }
        }
    }
    // TODO submission checks! check to make sure everything in $scope.playerData is an object (not a string. string = partially typed box)

    $http.get(hostname + $routeParams.region + '/tournaments/' + $scope.tournamentId).
        success($scope.updateData);
});

app.controller("PlayersController", function($scope, $routeParams, RegionService, PlayerService) {
    RegionService.setRegion($routeParams.region);
    $scope.regionService = RegionService;
    $scope.playerService = PlayerService;
});

app.controller("PlayerDetailController", function($scope, $http, $routeParams, $modal, RegionService, SessionService, PlayerService) {
    RegionService.setRegion($routeParams.region);
    $scope.regionService = RegionService;
    $scope.sessionService = SessionService;
    $scope.playerService = PlayerService;

    $scope.modalInstance = null;
    $scope.disableButtons = false;
    $scope.errorMessage = false;

    $scope.player = null;
    $scope.playerId = $routeParams.playerId;
    $scope.mergePlayer = "";
    $scope.matches = null;

    $scope.openDetailsModal = function() {
        $scope.modalInstance = $modal.open({
            templateUrl: 'player_details_modal.html',
            scope: $scope,
            size: 'lg'
        });

        $scope.postParams = {name: $scope.player.name}
        $scope.playerRegionCheckbox = {}

        $scope.sessionService.getAdminRegions().forEach(
            function(regionId){
                if($scope.isPlayerInRegion(regionId)){
                    $scope.playerRegionCheckbox[regionId] = "IN_REGION";
                }else{
                    $scope.playerRegionCheckbox[regionId] = "NOT_IN_REGION";
                }
            });

        $scope.disableButtons = false;
        $scope.errorMessage = false;
    };

    $scope.closeDetailsModal = function() {
        $scope.modalInstance.close()
    };

    $scope.updatePlayerDetails = function() {
        console.log("updating player details!");
        url = hostname + $routeParams.region + '/players/' + $scope.playerId;
        $scope.disableButtons = true;

        playerInRegion = function(regionId){
            return $scope.playerRegionCheckbox[regionId]!=="NOT_IN_REGION";
        };

        $scope.postParams['regions'] = $scope.sessionService.getAdminRegions().filter(playerInRegion);

        successCallback = function(data) {
            $scope.player = data;
            $scope.closeDetailsModal();
        };

        failureCallback = function(data) {
            $scope.disableButtons = false;
            $scope.errorMessage = true;
        };

        $scope.sessionService.authenticatedPut(url, $scope.postParams, successCallback, failureCallback);

        return;
    };

    $scope.isPlayerInRegion = function(regionId) {
        return $scope.player.regions.indexOf(regionId) > -1
    };

    $scope.submitMerge = function() {
        if ($scope.mergePlayer.id === undefined) {
            alert("You must select a player to merge");
            return;
        }
        url = hostname + $routeParams.region + '/merges';
        params = {"source_player_id": $scope.playerId, "target_player_id": $scope.mergePlayer.id};
        console.log(params);

        successCallback = function(data) {
            alert("These two accounts have been merged.");
            window.location.reload();
        };

        failureCallback = function(data) {
            alert("Your merge didn't go through. Please check that both players are in the region you administrate and try again later.");
        };
        $scope.sessionService.authenticatedPut(url, params,
            successCallback,
            failureCallback);
    };

    $scope.getMergePlayers = function(viewValue) {
        players = $scope.playerService.getPlayerListFromQuery(viewValue,
            function(player) {return player.id != $scope.playerId});
        return players;
    }

    $http.get(hostname + $routeParams.region + '/players/' + $routeParams.playerId).
        success(function(data) {
            $scope.player = data;
            console.log(data);
            if($scope.player.merged){
                $http.get(hostname + $routeParams.region + '/players/' + $scope.player.merge_parent).
                    success(function(data) {
                        $scope.mergeParent = data;
                    });
            }
        });

    $http.get(hostname + $routeParams.region + '/matches/' + $routeParams.playerId).
        success(function(data) {
            $scope.matches = data.matches.reverse();
        });

});

app.controller("MergesController", function($scope, $routeParams, $modal, RegionService, MergeService, SessionService) {
    RegionService.setRegion($routeParams.region);
    $scope.regionService = RegionService;
    $scope.mergeService = MergeService;
    $scope.sessionService = SessionService;

    $scope.undoMerge = function(mergeID) {
        url = hostname + $routeParams.region + '/merges/' + mergeID;

        successCallback = function(data) {
            alert("The accounts have successfully been unmerged.");
            window.location.reload();
        };

        $scope.sessionService.authenticatedDelete(url, successCallback);
    };
});

app.controller("HeadToHeadController", function($scope, $http, $routeParams, RegionService, PlayerService) {
    RegionService.setRegion($routeParams.region);
    $scope.regionService = RegionService;
    $scope.playerService = PlayerService;
    $scope.player1 = null;
    $scope.player2 = null;
    $scope.wins = 0;
    $scope.losses = 0;

    $scope.onChange = function() {
        if ($scope.player1 != null && $scope.player2 != null) {
            $http.get(hostname + $routeParams.region +
                '/matches/' + $scope.player1.id + '?opponent=' + $scope.player2.id).
                success(function(data) {
                    $scope.playerName = $scope.player1.name;
                    $scope.opponentName = $scope.player2.name;
                    $scope.matches = data.matches.reverse();
                    $scope.wins = data.wins;
                    $scope.losses = data.losses;
                });
        }
    };
});
