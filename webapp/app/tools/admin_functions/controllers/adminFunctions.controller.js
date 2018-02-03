angular.module('app.tools').controller("AdminFunctionsController", function($scope, $http, RegionService, SessionService){
    var url = hostname + "adminfunctions";
    $scope.regionService = RegionService;
    $scope.sessionService = SessionService;

    $scope.regions = []

    var updateRegions = function(){
        $http.get(hostname + 'regions').
            success(function(data) {
                $scope.regions = [];
                data.regions.forEach(function(region){
                    $scope.regions.push(region);
                });
            });
    }
    updateRegions();

    $scope.regionStatusMessage = "";
    $scope.userStatusMessage = "";

    $scope.oldPassword = "";
    $scope.newPassword = "";
    $scope.newPasswordRepeat = "";

    $scope.postParams = {
        function_type: '',
        new_region: '',
        new_user_name: '',
        new_user_pass: '',
        new_user_permissions: '',
        new_user_regions: []
    };

    $scope.addRegion = function(region){
        if(!$scope.postParams.new_user_regions.includes(region))
            $scope.postParams.new_user_regions.push(region);
    };

    $scope.removeRegion = function(region){
        if($scope.postParams.new_user_regions.includes(region))
            $scope.postParams.new_user_regions.splice($scope.postParams.new_user_regions.indexOf(region), 1);
    };

    $scope.changeRegionActiveTF = function(region){
        var region_id = region.id;
        var newIsActive  = !(region.is_active)

        var url = hostname + 'regions';
        var postParams = {
            region_id: region_id,
            is_active: newIsActive
        }

        $scope.sessionService.authenticatedPost(url, postParams,
            (data)=>{
                //alert(region_id + ' active flag changed to ' + newIsActive + '!');
                // TODO refresh the scope
                updateRegions();
                $scope.regionService.updateRegionDropdown();
            },
            (err)=>{
                if(err) {
                    alert(err.message);
                    return;
                }
            })
    }

    $scope.checkRegionBox = function(region){
        var display_name = region.display_name;
        var checkboxId = display_name + "_checkbox";
        var checkbox = document.getElementById(checkboxId);
        if(checkbox.checked){
            $scope.addRegion(region.id);
        }
        else{
            $scope.removeRegion(region.id);
        }
    };

    $scope.submitNewUser = function(){
        if($scope.postParams.new_user_name == null ||
            $scope.postParams.new_user_pass == null){
            return;
        }
        $scope.postParams.function_type = 'user';

        //TODO HTTP CALL TO API
        $scope.sessionService.authenticatedPut(url, $scope.postParams, $scope.putUserSuccess, $scope.putUserFailure);
    };

    $scope.submitNewRegion = function(){
        if($scope.postParams.new_region == null){
            return;
        }
        $scope.postParams.function_type = 'region';

        //TODO HTTP CALL TO API
        $scope.sessionService.authenticatedPut(url, $scope.postParams, $scope.putRegionSuccess, $scope.putRegionFailure);
    };

    $scope.putRegionSuccess = function(response, status, headers, bleh){
        console.log(response);
        $scope.regionStatusMessage = "Region " + $scope.postParams.new_region + " successfully inserted!";
        document.getElementById('regionStatusMessage').innerHTML
            = "Region " + $scope.postParams.new_region + " successfully inserted!";

        var form = document.getElementById('newRegionForm');
        resetForm(form);
        updateRegions();
    };

    $scope.putUserSuccess = function(response, status, headers, bleh){
        console.log(response);
        $scope.userStatusMessage = "User " + $scope.postParams.new_user_name + " successfully inserted!";
        document.getElementById('userStatusMessage').innerHTML
            = "User " + $scope.postParams.new_user_name + " successfully inserted!";

        var form = document.getElementById('newUserForm');
        resetForm(form);
    };

    $scope.putRegionFailure = function(response, status, headers, bleh){
        console.log(response);
        $scope.regionStatusMessage = "An error occurred in inserting user."
        document.getElementById('regionStatusMessage').innerHTML = "An error occurred in inserting region.";
    };

    $scope.putUserFailure = function(response, status, headers, bleh){
        console.log(response);
        $scope.userStatusMessage = "An error occurred in inserting user."
        document.getElementById('userStatusMessage').innerHTML = "An error occurred in inserting user.";
    };

    $scope.changePassword = function(){
        if(!($scope.newPassword === $scope.newPasswordRepeat)){
            //TODO Alert user to a mismatch and light the rows red
            alert('New passwords do not match!')
            return
        }

        //TODO send change request
        var url = hostname + 'user';
        var putParams = {
            old_pass: $scope.oldPassword,
            new_pass: $scope.newPassword
        }

        $scope.sessionService.authenticatedPut(url, putParams,
            (data)=>{
                alert('Password changed successfully!');
                // TODO clear the form
            },
            (err)=>{
                if(err) {
                    alert(err.message);
                    return;
                }
            })
    }

    function resetForm(form) {
        $scope.postParams = {
            function_type: '',
            new_region: '',
            new_user_name: '',
            new_user_pass: '',
            new_user_permissions: '',
            new_user_regions: []
        };
    };

});