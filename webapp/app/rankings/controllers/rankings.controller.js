angular.module('app.rankings').controller("RankingsController", function($scope, $http, $routeParams, $uibModal, TournamentService, RegionService, RankingsService, SessionService) {
    RegionService.setRegion($routeParams.region);
    $scope.regionService = RegionService;
    $scope.rankingsService = RankingsService;
    $scope.sessionService = SessionService;
    $scope.tournamentService = TournamentService;

    $scope.modalInstance = null;
    $scope.disableButtons = false;

    $scope.rankingNumDaysBack = 0;
    $scope.rankingsNumTourneysAttended = 0;
    $scope.tourneyNumDaysBack = 999;

    $scope.prompt = function() {
        $scope.modalInstance = $uibModal.open({
            templateUrl: 'app/rankings/views/generate_rankings_prompt_modal.html',
            scope: $scope,
            size: 'lg'
        });
    };

    $scope.getTournamentsInRange = function(){
        var now = new Date(Date.now());

        var then = new Date();
        then.setDate(then.getDate() - $scope.rankingNumDaysBack);

        $scope.rankingTournamentsList = $scope.tournamentService.getTournamentsInDateRange(now, then);
    }

    $scope.confirm = function() {
        $scope.disableButtons = true;
        url = hostname + $routeParams.region + '/rankings';
        successCallback = function(data) {
            $scope.rankingsService.rankingsList = data;
            $scope.modalInstance.close();
        };

        var postParams = {
            ranking_num_tourneys_attended: $scope.rankingsNumTourneysAttended,
            ranking_activity_day_limit: $scope.rankingNumDaysBack,
            tournament_qualified_day_limit: $scope.tourneyNumDaysBack
        }

        $scope.sessionService.authenticatedPost(url, postParams, successCallback, angular.noop);
    };

    $scope.cancel = function() {
        $scope.modalInstance.close();
    };

    $scope.getRegionRankingCriteria = function(){
        url = hostname + $routeParams.region + '/rankings';
        $http.get(url)
        .then(
        (res) => {
            $scope.rankingNumDaysBack = res.data.ranking_criteria.ranking_activity_day_limit;
            $scope.rankingsNumTourneysAttended = res.data.ranking_criteria.ranking_num_tourneys_attended;
            $scope.tourneyNumDaysBack = res.data.ranking_criteria.tournament_qualified_day_limit;
            
        },
        (err) => {
            alert('There was an error getting the Ranking Criteria for the region')
        });

    }

    $scope.saveRegionRankingsCriteria = function(){
        url = hostname + $routeParams.region + '/rankings';
        var putParams = {
            ranking_num_tourneys_attended: $scope.rankingsNumTourneysAttended,
            ranking_activity_day_limit: $scope.rankingNumDaysBack,
            tournament_qualified_day_limit: $scope.tourneyNumDaysBack
        }

        $scope.sessionService.authenticatedPut(url, putParams,
        (res) => {
            alert('Successfully updated Region: ' + $routeParams.region + ' Ranking Criteria.');
        },
        (err) => {
            alert('There was an error updating the Region Ranking Criteria. Please try again.');
        });
    };

    var rankingCriteria = $scope.getRegionRankingCriteria();
});