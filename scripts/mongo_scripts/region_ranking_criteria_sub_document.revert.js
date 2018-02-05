var r = db.regions.find();

r.forEach(region => {
    var num_tourneys = region.ranking_num_tourneys_attended || 2;
    var activity_day_limit = region.ranking_activity_day_limit || 60;
    var qualified_day_limit = region.tournament_qualified_day_limit || 999;

    db.regions.update(
        {"_id": region._id},
        {"$unset": {
                "region_renking_criteria": {
                    "ranking_num_tourneys_attended": "",
                    "ranking_activity_day_limit": "",
                    "tournament_qualified_day_limit": ""
                }
            }
        }
    )

    db.regions.update(
        {"_id": region._id},
        {"$set": {
            "ranking_num_tourneys_attended": "", 
            "ranking_activity_day_limit": "",
            "tournament_qualified_day_limit": ""
            }
        }
    )
})

//Run this if there are any undefined values
var r = db.regions.find();

r.forEach(region => {
    var num_tourneys = region.ranking_num_tourneys_attended || 2;
    var activity_day_limit = region.ranking_activity_day_limit || 60;
    var qualified_day_limit = region.tournament_qualified_day_limit || 999;

    db.regions.update(
        {"_id": region._id},
        {"$set": {
                "ranking_num_tourneys_attended": num_tourneys,
                "ranking_activity_day_limit": activity_day_limit,
                "tournament_qualified_day_limit": qualified_day_limit
            }
        }
    )
})