angular.module('app.tournaments').service('TournamentService', function() {
    var service = {
        tournamentList: null,
        excludedList: [],
        getTournamentsInDateRange: function(startDate, endDate){
            if(service.tournamentList){
                var subset = _.filter(service.tournamentList, function(t){
                    return new Date(t.date) >= startDate && new Date(t.date) <= endDate;
                })
                return subset;
            }
        },
        getTournamentById: function(id){
            var tournament = _.find(service.tournamentList, {_id: id});
            return tournament;
        },
        getTournamentsByIds: function(idList){
            if(idList && idList.length > 0 && 
                service.tournamentList && 
                service.tournamentList.length > 0){

                var tournaments = [];
                idList.forEach(function(id) {
                    var t = _.find(service.tournamentList, {id, id});
                    tournaments.push(t);
                });
                return tournaments.reverse();

            }
        }
    };
    return service;
});