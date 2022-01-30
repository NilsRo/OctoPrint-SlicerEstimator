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

    //Activate flag filelist
    self.filelistEnabled = ko.pureComputed(function() {
      return self.settingsViewModel.settings.plugins.SlicerEstimator.metadata() && self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_filelist()
    });

    //Activate flag printer
    self.printerEnabled = ko.pureComputed(function() {
      return self.settingsViewModel.settings.plugins.SlicerEstimator.metadata() && self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_printer()
    });

    // Overwrite the enableAdditionalData function to handle available metadata
    self.filesViewModel.slicerEnableAdditionalData = function(data) {            
      if (data.slicer != null && Object.keys(data.slicer).length > 0 && self.filelistEnabled()) {
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
      if (data.slicer != null && Object.keys(data.slicer).length > 0 && self.filelistEnabled()) {
        for (const [key, value] of Object.entries(data.slicer)) {
          meta = self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list().find(elem => elem.id() === key && elem.filelist());
          let description = "No description";
          if (meta != null) {
            description = meta.description();
            return_value += description + ": " + value + "<br>";
          }
        }
      }
      if (self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_filelist_align() === "top") {
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
                description: ko.observable(slicerData).extend({ stripQuotes: true}),
                filelist: ko.observable(false),
                printer: ko.observable(false)                
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
        let enabledMeta = self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list().filter(elem => elem.printer() === true);
        let actualFile = self.filesViewModel.filesOnlyList().find(elem => elem.path === self.printerStateViewModel.filepath() && elem.slicer != null);
        if (typeof actualFile !== 'undefined') {        
          enabledMeta.forEach(function(data) {                     
            if (actualFile.slicer != null && Object.keys(actualFile.slicer).length > 0) {
              item = actualFile.slicer[data.id()];              
              if (item != null) {
                let returnArr = [];
                returnArr["description"] = data.description;
                returnArr["value"] = item;
                returnMeta.push(returnArr);
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
      if (self.printerEnabled()) {
        var element = $("#state").find(".accordion-inner .progress");
        if (element.length) {
          element.before("<div id='metadata_list' data-bind='foreach: currentMetadata'><span data-bind='text: description'></span>: <strong data-bind='text: value'> - </strong><br></div>");
        }
      }
    };

    //Switch tab in settings on/off
    self.settingsViewModel.customTabCss = ko.pureComputed(function() {
      if (self.settingsViewModel.settings.plugins.SlicerEstimator.slicer() === "c") {
        return "show";
      } else {
        return "hide";
      }
    });

    //Switch tab in settings on/off
    self.settingsViewModel.metadataTabCss = ko.pureComputed(function() {
      if (self.settingsViewModel.settings.plugins.SlicerEstimator.metadata()) {
        return "show";
      } else {
        return "hide";
      }
    });


    // --- Settings Report Bug
    self.settingsViewModel.createIssue = function() {
      // Send the bug report      
      url = 'https://github.com/NilsRo/OctoPrint-SlicerEstimator/issues/new';
      var body = "## Description\n**ENTER DESCRIPTION HERE\nDescribe your problem?\nWhat is the problem?\nCan you recreate it?\nDid you try disabling plugins?\nDid you remember to update the subject?**\n\n\n**Plugins installed**\n";
      
      // Get plugin info
      OctoPrint.coreui.viewmodels.pluginManagerViewModel.plugins.allItems.forEach(function(item) {
        if (item.enabled && item.bundled == false){
          var version = "";
          if (item.version != null){
            version = " v"+ item.version;
          }
          body += '- ' + item.name +"["+item.key+"]" + version + "\n";
          }
      });      
      
      // Settings
      body += "\n\n**Settings**\n";      
      Object.entries(self.settingsViewModel.settings.plugins.SlicerEstimator).forEach(function(item) {
        if (item[0] == 'metadata_list') {
          body += '- ' + item[0] + ": ";
          item[1]().forEach(function(meta_item) {
            body += ' (id: ' + meta_item["id"](); 
            body += ', description: ' + meta_item["description"](); 
            body += ', printer: ' + meta_item["printer"](); 
            body += ', filelist: ' + meta_item["filelist"]() + '); '; 
          });
          body += "\n";
        } else {
          body += '- ' + item[0] + ": " +item[1]() + "\n";
        }

      });
      body += "\n\n**Software versions**\n- "+$('#footer_version li').map(function(){return $(this).text()}).get().join("\n- ");
      body += "\n\n\n**Browser**\n- "+navigator.userAgent
      window.open(url+'?body='+encodeURIComponent(body));      
    };
  }

  
  OCTOPRINT_VIEWMODELS.push({
    construct: slicerEstimatorViewModel,
    dependencies: ["printerStateViewModel", "filesViewModel", "settingsViewModel"],
    elements: ['#metadata_list']
  });
});