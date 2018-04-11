angular.module('app.tournaments').controller("TournamentsController", function($scope, $http, $routeParams, $uibModal, RegionService, TournamentService, SessionService) {
    RegionService.setRegion($routeParams.region);
    $scope.regionService = RegionService;
    $scope.tournamentService = TournamentService;
    $scope.sessionService = SessionService;

    $scope.modalInstance = null;
    $scope.disableButtons = false;
    $scope.errorMessage = false;

    $scope.smashGG_brackets = [];
    $scope.postParams = {};
    $scope.included_phases = [];

    $scope.smashGGImportMessage = "";

    $scope.isMatchCurrentlyExcluded = function(tournament){
        var excluded = tournament.excluded;

        if(excluded){
            var lineId = 'tournament_line_' + tournament.id;
            var lineElement = document.getElementById(lineId);
            lineElement.className = 'tournament_line excluded ng-scope';
        }

        return excluded;
    }

    $scope.changeTournamentExclusion = function(tournament){

        //var idx = $scope.sessionService.indexOf(tournament);
        var url = hostname + $routeParams.region + '/tournaments/' + tournament.id;

        var checkboxId = 'exclude_tournament_checkbox_' + tournament.id;
        var lineId = 'tournament_line_' + tournament.id;

        var checkboxElement = document.getElementById(checkboxId);
        var lineElement = document.getElementById(lineId);

        var postParams = {
            excluded_tf: false
        }

        // is currently selected
        if (checkboxElement.checked) {
          // TODO send true to the api
          postParams.excluded_tf = true;
          $scope.sessionService.authenticatedPost(url, postParams,
            (data) => {
                // TODO remove tournament from excluded list

                // TODO paint the row grey
                lineElement.className += ' excluded'
                $scope.regionService.setTournamentExcluded(tournament.id, true);
                return;
            },
            (err) => {
                if(err){
                    console.log(err.message);
                }
            })
        }
        else {
          // TODO send false to the api
          $scope.sessionService.authenticatedPost(url, postParams,
            (data) => {
                // TODO add tournament to excluded list

                // TODO unpaint the grey row
                lineElement.className = '';
                lineElement.className = 'tournament_line ng-scope';

                $scope.regionService.setTournamentExcluded(tournament.id, false);
                return;
            },
            (err) => {
                if(err){
                    console.log(err.message);
                }
            })
        }
    };


    $scope.toggleExcludedTournament = function(tournament) {

    };

    $scope.open = function() {
        $scope.disableButtons = false;
        $scope.modalInstance = $uibModal.open({
            templateUrl: 'app/tournaments/views/import_tournament_modal.html',
            scope: $scope,
            size: 'lg'
        });

        //Handle if modal is closed or dismissed
        $scope.modalInstance.result.then(function(){
            $scope.clearSmashGGData();
        }, function(){
            $scope.clearSmashGGData();
        });
    };

    $scope.setBracketType = function(bracketType) {
        $scope.postParams = {};
        $scope.postParams.type = bracketType;
        $scope.errorMessage = false;
    };

    $scope.close = function() {
        $scope.clearSmashGGData();
        $scope.modalInstance.close();
    };

    $scope.clearSmashGGData = function(){
        $scope.smashGG_brackets = [];
        $scope.included_phases = [];
        $scope.smashGGImportMessage.innerHTML = "";

    };

    $scope.submit = function() {
        $scope.disableButtons = true;
        $scope.postParams.included_phases = $scope.included_phases;

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
        document.getElementById('smashGGImportMessage').innerHTML = "";
    };

    $scope.loadFile = function(fileContents) {
        $scope.postParams.data = fileContents;
    };

    $scope.openDeleteTournamentModal = function(tournamentId) {
        $scope.modalInstance = $uibModal.open({
            templateUrl: 'app/tournaments/views/delete_tournament_modal.html',
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


    $scope.checkSmashggBracket = function(bracket){
        var id = bracket.id;
        var checkboxId = id + "_checkbox";
        var checkbox = document.getElementById(checkboxId);
        if(checkbox.checked){
            //CHECKED: INCLUDE PHASE ID FOR INCLUSION
            if(!$scope.included_phases.includes(id))
                $scope.included_phases.push(id);
        }
        else{
            // NOT CHECKED: DON'T INCLUDE PHASE ID IN POST REQUEST
            if($scope.included_phases.includes(id))
                $scope.included_phases.splice($scope.included_phases.indexOf(id), 1);
        }
    }


    //RETRIEVE THE PHASE ID TO BRACKET NAME MAP
    $scope.smashGG_populateBrackets = function(){
        $scope.disableButtons = true;
        if($scope.postParams.data === ''){
            $scope.smashGG_brackets = [];
            document.getElementById('smashGGImportMessage').innerHTML = "";
            return;
        }else{
            document.getElementById('smashGGImportMessage').innerHTML = "Importing Phases. Please wait...";
        }

        var url = hostname + 'smashGgMap';
        $http.get( url, {
            params: {
                bracket_url: $scope.postParams.data
            }
        }).
        success(function(data) {
            for(var key in data){
                var bracket = {
                    name: data[key],
                    id: key
                };
                $scope.smashGG_brackets.push(bracket);
            };
            $scope.disableButtons = false;
            document.getElementById('smashGGImportMessage').innerHTML = "Please choose the phases to include";
        }).
        error(function(data) {
            document.getElementById('smashGGImportMessage').innerHTML = "Something went wrong. Please try again. " +
                "\nIf the problem persists, please contact the Admins";
        });
    };
});
