/*
 * View model for OctoPrint-SlicerEstimator
*/

$(function() {
  function slicerEstimatorViewModel(parameters) {
    var self = this;

    self.printerStateViewModel = parameters[0];
    self.filesViewModel = parameters[1];
    self.settingsViewModel = parameters[2];

    // --- Estimator 

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
    
    //--- Additional Metadata filelist

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


    //--- Additional Metadata current print

    //Delete an entry in the settings
    self.settingsViewModel.deleteMeta = function(data) {
      let delIndex = self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list().findIndex(elem => elem.id() === data.id());
      self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list.splice(delIndex,1);
    };

    // Update available metadata from files in the settings
    self.settingsViewModel.crawlMetadata = function() {
      self.filesViewModel.filesOnlyList().forEach(function (data) {
        Object.keys(data.slicer).forEach(function (slicerData) {
          if (self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list().find(elem => elem.id() === slicerData) == null) {
            var meta = {
                id: ko.observable(slicerData).extend({ stripQuotes: true}),
                desc: ko.observable(data.slicer[slicerData][0]).extend({ stripQuotes: true}),
                enabled: ko.observable(false)
            };
            self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list.push(meta);
          }
        });
      });
    };

    //get list of enabled metadata
    self.currentMetadata = ko.pureComputed(function() {
      var returnMeta = [];
      if (typeof self.printerStateViewModel.filepath() !== 'undefined') {
        let enabledMeta = self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list().filter(elem => elem.enabled() === true);
        let actualFile = self.filesViewModel.filesOnlyList().find(elem => elem.path === self.printerStateViewModel.filepath() && elem.slicer != null);
        if (typeof actualFile !== 'undefined') {        


          enabledMeta.forEach(function(data) {                     
            if (actualFile.slicer != null && Object.keys(actualFile.slicer).length > 0) {
              item = actualFile.slicer[data.id()];
              if (item != null) {                
                returnMeta.push(item);
              }            
            }
          })
        }
      }      
      return returnMeta;
    });    

    //enhance printerViewModel
    self.onBeforeBinding = function() {
      // inject filament metadata into template
      if (self.settingsViewModel.settings.plugins.SlicerEstimator.add_slicer_current()) {
        var element = $("#state").find(".accordion-inner .progress");
        if (element.length) {
          element.before("<div id='metadata_list' data-bind='foreach: currentMetadata'><span data-bind='text: $data[0]'></span>: <strong data-bind='text: $data[1]'> - </strong><br></div>");
        }
      }
    };

    self.settingsViewModel.customTabCss = ko.pureComputed(function() {
      if (self.settingsViewModel.settings.plugins.SlicerEstimator.slicer() === "c") {
        return "show";
      } else {
        return "hide";
      }
    });

    self.settingsViewModel.metadataTabCss = ko.pureComputed(function() {
      if (self.settingsViewModel.settings.plugins.SlicerEstimator.add_slicer_current()) {
        return "show";
      } else {
        return "hide";
      }
    });
  }

  
  OCTOPRINT_VIEWMODELS.push({
    construct: slicerEstimatorViewModel,
    dependencies: ["printerStateViewModel", "filesViewModel", "settingsViewModel"],
    elements: ['#metadata_list']
  });
});