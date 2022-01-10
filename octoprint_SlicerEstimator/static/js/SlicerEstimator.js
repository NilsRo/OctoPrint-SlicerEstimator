/*
 * View model for OctoPrint-SlicerEstimator
*/

$(function() {
  function slicerEstimatorViewModel(parameters) {
    var self = this;

    self.printerStateViewModel = parameters[0];
    self.filesViewModel = parameters[1];
    self.settingsViewModel = parameters[2];


    
    // Overwrite the printTimeLeftOriginString function
    ko.extenders.addSlicerEstimator = function(target, option) {
      let result = ko.pureComputed(function () {
        let value = self.printerStateViewModel.printTimeLeftOrigin();
        switch (value) {
          case "slicerestimator": {
            return option;
          }
          default: {
            return target();
          }
        }
      });
      return result;
    };

    // Add the new hover text
    self.printerStateViewModel.printTimeLeftOriginString =
        self.printerStateViewModel.printTimeLeftOriginString.extend({
          addSlicerEstimator: gettext("Based on information added by the slicer.")});

    // Overwrite the printTimeLeftOriginClass function
    self.originalPrintTimeLeftOriginClass = self.printerStateViewModel.printTimeLeftOriginClass;
    self.printerStateViewModel.printTimeLeftOriginClass = ko.pureComputed(function() {
      let value = self.printerStateViewModel.printTimeLeftOrigin();
      switch (value) {
        case "slicerestimator": {
          return "slicerestimator";
        }
        default: {
          return self.originalPrintTimeLeftOriginClass();
        }
      }
    });
    self.printerStateViewModel.printTimeLeftOrigin.valueHasMutated();


    //API Example - actually not used---------------------------------------------------------------
    // self.get_api_data = function(){
    //   self.filament_results([]);

    //   $.ajax({
    //     url: API_BASEURL + "plugin/SlicerEstimator",
    //     type: "POST",
    //     dataType: "json",
    //     data: JSON.stringify({
    //       command: "getSlicerData"
    //     }),
    //     contentType: "application/json; charset=UTF-8"
    //   }).done(function(data){
    //     for (key in data) {
    //       if(data[key].length){
    //         self.filament_results.push({name: ko.observable(key), filament: ko.observableArray(data[key])});
    //       }
    //     }
    //     self.filesViewModel.requestData({force: true});
    //   })
    // };
    
    // Overwrite the enableAdditionalData function to handle available metadata
    self.filesViewModel.slicerEnableAdditionalData = function(data) {      
      if (data.slicer != null && Object.keys(data.slicer).length > 0 && self.settingsViewModel.settings.plugins.SlicerEstimator.add_slicer_metadata() == true) {
          return true;
      } else {
          return self.filesViewModel.originalEnableAdditionalData(data);
      }
    };
    self.filesViewModel.originalEnableAdditionalData = self.filesViewModel.enableAdditionalData;
    self.filesViewModel.enableAdditionalData = self.filesViewModel.slicerEnableAdditionalData;

    //Add the slicer metadata to "additionalMetadata"
    self.filesViewModel.getSlicerData = function(data) {
      let return_value = "";
      if (data.slicer != null && Object.keys(data.slicer).length > 0 && self.settingsViewModel.settings.plugins.SlicerEstimator.add_slicer_metadata() == true) {
        for (const [key, value] of Object.entries(data.slicer)) {
          return_value += value[0] + ": " + value[1] + "<br>";
        }
      }
      if (self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_orientation() === "top") {
        return_value += self.filesViewModel.originalGetAdditionalData(data);
      } else {
        return_value = self.filesViewModel.originalGetAdditionalData(data) + return_value;
      }
      return return_value;
    };
    self.filesViewModel.originalGetAdditionalData = self.filesViewModel.getAdditionalData;
    self.filesViewModel.getAdditionalData = self.filesViewModel.getSlicerData;

    //Old: Add the slicer metadata array to HTML DOM
    // self.onBeforeBinding = function() {
    //   // inject filament metadata into template
    //   if (self.settingsViewModel.settings.plugins.SlicerEstimator.add_slicer_metadata() == true) {
    //     $("#files_template_machinecode").text(function () {
    //       let return_value = $(this).text();
    //       let regex = /<div class="additionalInfo hide"/mi;
    //       return_value = return_value.replace(regex, '<div class="additionalInfo hide" data-bind="html: $root.getSlicerData($data)"></div> <div class="additionalInfo hide"');
    //       return return_value
    //     });
    //   }
    // };

    self.settingsViewModel.customTabCss = ko.pureComputed(function() {
      if (self.settingsViewModel.settings.plugins.SlicerEstimator.slicer() === "c") {
        return "show";
      } else {
        return "hide";
      }
    });
  }
  /* view model class, parameters for constructor, container to bind to
   * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
   * and a full list of the available options.
   */

  
  OCTOPRINT_VIEWMODELS.push({
    construct: slicerEstimatorViewModel,
    dependencies: ["printerStateViewModel", "filesViewModel", "settingsViewModel"],
    elements: ['#getSlicerData']
  });
});