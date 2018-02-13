angular.module('app.rankings').service('RankingsService', function($http, SessionService) {
    var service = {
        rankingsList: null,
        rankingsTournaments: null,
        rankingsTournamentsIds: null
    };
    return service;
});