/*
 * View model for OctoPrint-SlicerEstimator
*/

$(function () {
  function slicerEstimatorViewModel(parameters) {
    var self = this;

    self.printerStateViewModel = parameters[0];
    self.filesViewModel = parameters[1];
    self.settingsViewModel = parameters[2];

    self.currentMetadataArr = ko.observableArray([]);
    self.actualFileMetadata;
    self.currentEstimatedPrinttime = ko.observable();
    self.filamentChangeArr = ko.observableArray([]);
    self.deleteMetadataStoredRunning = ko.observable(false);
    self.updateMetadataStoredRunning = ko.observable(false);

    //Helpers
    self.mapDictionaryToArray = function (dictionary) {
      var result = [];
      for (var key in dictionary) {
        if (dictionary.hasOwnProperty(key)) {
          result.push({ key: key, value: dictionary[key] });
        }
      }
      return result;
    };

    self.filamentChangeTimeFormat = function (changeTime) {
      let fmt = self.settingsViewModel.appearance_fuzzyTimes()
        ? formatFuzzyPrintTime
        : formatDuration;
      return fmt(changeTime);
    };

    self.filamentChangeType = function (changeType) {
      if (changeType == "M600") {
        return gettext("filament change (M600)");
      } else if (changeType.substring(0, 1) == "T") {
        return gettext("filament") + " (" + gettext("tool") + " " + changeType.substring(1, 2) + ")";
      } else if (changeType == "M0" || changeType == "M601") {
        return gettext("pause") + " (" + changeType + ")";
      }
    };

    // receive data from server
    self.onDataUpdaterPluginMessage = function (plugin, data) {
      // Event
      if (data.eventID) {
        switch (data.eventID) {
          case "file_metadata_updated":
            // Update file list metadata
            self.filesViewModel.requestData({ force: true });
        }
      }


      // NotificationMessages
      if (data.notifyType) {
        var notfiyType = data.notifyType;
        var notifyTitle = data.notifyTitle;
        var notifyMessage = data.notifyMessage;
        var notifyHide = data.notifyHide;
        new PNotify({
          title: notifyTitle,
          text: notifyMessage,
          type: notfiyType,
          hide: notifyHide
        });
      }
      if (data.notifyMessageID) {
        switch (data.notifyMessageID) {
          case "no_estimation":
            new PNotify({
              title: "Slicer Estimator",
              text: gettext("No print time estimation from slicer available. Please upload GCODE file again. The file was uploaded before Slicer Estimator was installed or Slicer was not detected."),
              type: "info",
              hide: true
            });
            break;
          case "file_metadata_updated":
            new PNotify({
              title: "Slicer Estimator",
              text: gettext("For the selected file the metadata was missing. It is updated now, refresh the filelist if you like to see the metadata found."),
              type: "info",
              hide: true
            });
            break;
          case "no_slicer_detected":
            new PNotify({
              title: "Slicer Estimator",
              text: gettext("Slicer not detected. Please open a ticket if the slicer should be known..."),
              type: "warning",
              hide: false
            });
            break;
          case "no_timecodes_found":
            new PNotify({
              title: "Slicer Estimator",
              text: gettext("No timecodes found. Please check if the remaining time feature in the slicer is active."),
              type: "warning",
              hide: false
            });
        }
      }
    };


    // --- Estimator
    self.estimatedPrintTimeString = self.printerStateViewModel.estimatedPrintTimeString;
    self.printerStateViewModel.estimatedPrintTimeString = ko.pureComputed(function () {
      if (self.printerStateViewModel.estimatedPrintTime() != null && self.currentEstimatedPrinttime() == self.printerStateViewModel.estimatedPrintTime()) {
        return self.estimatedPrintTimeString() + " ✔";
      } else {
        return self.estimatedPrintTimeString();
      }
    });


    // Overwrite the printTimeLeftOriginString function
    ko.extenders.addSlicerEstimator = function (target, option) {
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
        addSlicerEstimator: gettext("Based on information added by the slicer.")
      });

    // Overwrite the printTimeLeftOriginClass function
    self.originalPrintTimeLeftOriginClass = self.printerStateViewModel.printTimeLeftOriginClass;
    self.printerStateViewModel.printTimeLeftOriginClass = ko.pureComputed(function () {
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
    self.filelistEnabled = ko.pureComputed(function () {
      return self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_filelist()
    });

    //Activate flag printer
    self.printerEnabled = ko.pureComputed(function () {
      return self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_printer()
    });

    // Overwrite the enableAdditionalData function to handle available metadata
    self.filesViewModel.slicerEnableAdditionalData = function (data) {
      if ((data.slicer_metadata != null && Object.keys(data.slicer_metadata).length > 0) || (data.slicer_filament_change != null && Object.keys(data.slicer_filament_change).length > 0)) {
        return true;
      } else {
        return self.filesViewModel.originalEnableAdditionalData(data);
      }
    };
    self.filesViewModel.originalEnableAdditionalData = self.filesViewModel.enableAdditionalData;
    self.filesViewModel.enableAdditionalData = self.filesViewModel.slicerEnableAdditionalData;

    //Add the slicer metadata to "additionalMetadata"
    self.filesViewModel.getSlicerData = function (data) {
      let return_value = "";
      //custom metadata
      if (data.slicer_metadata != null && Object.keys(data.slicer_metadata).length > 0) {
        for (const [key, value] of Object.entries(data.slicer_metadata)) {
          meta = self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list().find(elem => elem.id() === key && elem.targets["SlicerEstimator"]["filelist"]() === true);
          let description = "No description";
          if (meta != null) {
            description = meta.description();
            return_value += description + ": " + value + "<br>";
          }
        }
        //filament changes
        if (data.slicer_filament_change != null && Object.keys(data.slicer_filament_change).length > 0 && data.slicer_additional != null && Object.keys(data.slicer_additional).length > 0 && data.slicer_additional["printtime"] != null) {
          let cnt = 0;
          for (const [key, value] of Object.entries(data.slicer_filament_change)) {
            cnt += 1;
            let changeTimeString;
            if (value[1] == null) {
              changeTimeString = self.filamentChangeTimeFormat(data.slicer_additional["printtime"] * (value[3] / data.size));
            } else {
              changeTimeString = self.filamentChangeTimeFormat(data.slicer_additional["printtime"] - value[1]);
            }
            return_value += cnt + ". " + self.filamentChangeType(value[0]) + ": " + changeTimeString + '<br>';
          }
        }

        if (self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_filelist_align() === "top") {
          return_value += self.filesViewModel.originalGetAdditionalData(data);
        } else {
          return_value = self.filesViewModel.originalGetAdditionalData(data) + return_value;
        }

        return return_value;
      } else {
        return self.filesViewModel.originalGetAdditionalData(data)
      }
    };
    self.filesViewModel.originalGetAdditionalData = self.filesViewModel.getAdditionalData;
    self.filesViewModel.getAdditionalData = self.filesViewModel.getSlicerData;


    //--- Additional Metadata current print

    // load file metadata
    self.getSlicerMetadata = function (origin, path) {
      // start jquery request for metadata
      OctoPrint.files.get(origin, path)
        .done(function (response) {
          let enabledMeta = self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list().filter(elem => elem.targets["SlicerEstimator"]["printer"]() === true);
          actualFileMetadata = response;
          self.currentMetadataArr.removeAll();
          if (typeof actualFileMetadata !== 'undefined') {

            self.currentEstimatedPrinttime(actualFileMetadata.slicer_additional['printtime']);

            enabledMeta.forEach(function (data) {
              if (actualFileMetadata.slicer_metadata != null && Object.keys(actualFileMetadata.slicer_metadata).length > 0) {
                item = actualFileMetadata.slicer_metadata[data.id()];
                if (item != null) {
                  let returnArr = [];
                  returnArr["description"] = data.description;
                  returnArr["value"] = item;
                  self.currentMetadataArr.push(returnArr);
                }
              }
            });
          }
          // Update visible metadata after refresh from API.
          self.addMetadata(origin, path);
        });
    }


    // adds metadata to printerStateViewModel
    self.addMetadata = function (origin, path) {
      debugger;
      if (typeof actualFileMetadata !== 'undefined' && actualFileMetadata.slicer_additional != null) {
        if (actualFileMetadata.slicer_filament_change != null && Object.keys(actualFileMetadata.slicer_filament_change).length > 0) {
          changeList = actualFileMetadata.slicer_filament_change;
          if (changeList != null) {
            let cnt = 0
            for (let item of changeList) {
              let changeTime;
              if (item[1] != null) {
                // SlicerEstimator based calculation - time
                if (self.printerStateViewModel.printTimeLeft() === null) {
                  changeTime = self.printerStateViewModel.estimatedPrintTime() - item[1];
                } else {
                  changeTime = (self.printerStateViewModel.estimatedPrintTime() - item[1]) - (self.printerStateViewModel.estimatedPrintTime() - self.printerStateViewModel.printTimeLeft());
                }
              } else {
                // progress based calculation
                changeTime = (self.printerStateViewModel.estimatedPrintTime() * (item[2] / self.printerStateViewModel.filesize())) - ((self.printerStateViewModel.estimatedPrintTime() * (item[2] / self.printerStateViewModel.filesize())) * (self.printerStateViewModel.filepos() / item[2]))
              }
              let changeTimeString = self.filamentChangeTimeFormat(changeTime);
              if (self.filamentChangeArr().length <= cnt) {
                let returnArr = {
                  description: ko.observable((cnt + 1) + ". " + self.filamentChangeType(item[0])),
                  value: ko.observable(changeTimeString),
                  title: ko.observable(formatDuration(changeTime))
                };
                self.filamentChangeArr.push(returnArr);
              } else {
                self.filamentChangeArr()[cnt].value(changeTimeString);
                self.filamentChangeArr()[cnt].title(formatDuration(changeTime));
              }
              cnt += 1;
            }
          }
        }
      }
    };

    //get list of enabled metadata and filament change if a file is selected
    self.addMetadataLocal = function (filepath) {
      if (self.printerStateViewModel.sd() == false && filepath !== null) {
        self.addMetadata("local", filepath);
      }
    };
    self.getSlicerMetadataLocal = function (filepath) {
      self.filamentChangeArr.removeAll();
      if (self.printerStateViewModel.sd() == false && filepath !== null) {
        self.getSlicerMetadata("local", filepath);
      }
    };

    self.printerStateViewModel.filepath.subscribe(function (filepath) { self.getSlicerMetadataLocal(filepath); });
    // self.printerStateViewModel.printTimeLeft.subscribe(function () { self.addMetadataLocal(self.printerStateViewModel.filepath()) });
    // self.printerStateViewModel.estimatedPrintTime.subscribe(function () { self.addMetadataLocal(self.printerStateViewModel.filepath()) });
    self.printerStateViewModel.filepos.subscribe(function () { self.addMetadataLocal(self.printerStateViewModel.filepath()); });

    //on reload if GUI refresh selected file
    ko.when(function () {
      return self.printerStateViewModel.sd() !== undefined && self.printerStateViewModel.filepath() !== undefined;
    }, function (result) {
      if (result == true && self.printerStateViewModel.sd() == false && self.printerStateViewModel.filepath() !== null) {
        self.getSlicerMetadata("local", self.printerStateViewModel.filepath());
        self.addMetadata("local", self.printerStateViewModel.filepath());
      }
    });

    //reset metadata list in printerStateViewModel
    self.removeMetadata = function () {
      self.filamentChangeArr.removeAll();
      self.currentMetadataArr.removeAll();
    };

    self.onEventFileDeselected = self.removeMetadata;
    self.onEventDisconnected = self.removeMetadata;


    //enhance printerStateViewModel
    self.onBeforeBinding = function () {
      // inject filament metadata into template
      if (self.printerEnabled()) {
        var element = $("#state").find(".accordion-inner .progress");
        if (element.length) {
          element.before(
            "<div id='filamentChange_list' data-bind='foreach: filamentChangeArr'><span data-bind='text: description'></span>: <strong data-bind='text: value, attr: {title: title}' title=' - '> - </strong><br></div>"
            + "<div id='metadata_list' data-bind='foreach: currentMetadataArr'><span data-bind='text: description'></span>: <strong data-bind='text: value'> - </strong><br></div>"
          );
        }
      }
    };


    //--- Settings
    self.settingsViewModel.selectedPlugin = ko.observable();
    self.settingsViewModel.filterTable = ko.observable('');


    //Delete an entry in the settings
    self.settingsViewModel.deleteMeta = function (data) {
      let delIndex = self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list().findIndex(elem => elem.id() === data.id());
      self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list.splice(delIndex, 1);
    };


    self.getActivePlugins = function () {
      return Object.entries(self.settingsViewModel.settings.plugins.SlicerEstimator.plugins).filter(elem => elem[1]["targets"] != null);
    };

    // Update available metadata from files in the settings
    self.settingsViewModel.crawlMetadata = function () {
      self.filesViewModel.filesOnlyList().forEach(function (data) {
        if (data.slicer_metadata != null) {
          Object.keys(data.slicer_metadata).forEach(function (slicerData) {
            if (self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list().find(elem => elem.id() === slicerData) == null) {
              let targets = {};
              for (plugin of self.getActivePlugins()) {
                targets[plugin[0]] = {};
                for (key of Object.keys(plugin[1]["targets"])) {
                  targets[plugin[0]][key] = ko.observable(false);
                }
              }
              var meta = {
                id: ko.observable(slicerData).extend({ stripQuotes: true }),
                description: ko.observable(slicerData).extend({ stripQuotes: true }),
                targets: targets
              };
              self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list.push(meta);
            }
          });
        };
      });
    };
    // Delete available metadata from list
    self.settingsViewModel.deleteMetadataList = function () {
      //TODO: Sicherheitsabfrage ergänzen
      self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list.removeAll();
    };

    // Delete all metadata stored
    self.deleteMetadataStored = function () {
      self.deleteMetadataStoredRunning(true);
      $.ajax({
        url: API_BASEURL + "plugin/SlicerEstimator",
        type: "POST",
        dataType: "json",
        data: JSON.stringify({
          command: "deleteMetadataStored"
        }),
        contentType: "application/json; charset=UTF-8"
      }).done(function (data) {
        for (key in data) {
          // if(data[key].length){
          // 	self.crawl_results.push({name: ko.observable(key), files: ko.observableArray(data[key])});
          // }
        }

        console.log(data);
        // if(self.crawl_results().length === 0){
        // 	self.crawl_results.push({name: ko.observable('No convertible files found'), files: ko.observableArray([])});
        // }
        // self.filesViewModel.requestData({force: true});
        self.deleteMetadataStoredRunning(false);
      }).fail(function (data) {
        self.deleteMetadataStoredRunning(false);
      });
    };

    // Update all metadata stored
    self.updateMetadataStored = function () {
      self.updateMetadataStoredRunning(true);
      $.ajax({
        url: API_BASEURL + "plugin/SlicerEstimator",
        type: "POST",
        dataType: "json",
        data: JSON.stringify({
          command: "updateMetadataStored"
        }),
        contentType: "application/json; charset=UTF-8"
      }).done(function (data) {
        for (key in data) {
          // if(data[key].length){
          // 	self.crawl_results.push({name: ko.observable(key), files: ko.observableArray(data[key])});
          // }
        }

        console.log(data);
        // if(self.crawl_results().length === 0){
        // 	self.crawl_results.push({name: ko.observable('No convertible files found'), files: ko.observableArray([])});
        // }
        // self.filesViewModel.requestData({force: true});
        self.updateMetadataStoredRunning(false);
      }).fail(function (data) {
        self.updateMetadataStoredRunning(false);
      });
    };

    self.settingsViewModel.pluginsSelection = function () {
      var returnArr = [];
      for (plugin of self.getActivePlugins()) {
        let plugin_identifier = plugin[0];
        let targets = plugin[1]["targets"];
        let plugin_name = plugin[1]["name"];
        for (const key of Object.keys(targets)) {
          returnArr.push({ plugin_identifier: plugin_identifier, plugin_name: plugin_name, target: key, target_name: targets[key] });
        }
      }
      return returnArr;
    };

    self.settingsViewModel.selectedPluginId = ko.pureComputed(function () {
      return self.settingsViewModel.selectedPlugin() && self.settingsViewModel.selectedPlugin().plugin_identifier;
    });

    self.settingsViewModel.selectedPluginTarget = ko.pureComputed(function () {
      return self.settingsViewModel.selectedPlugin() && self.settingsViewModel.selectedPlugin().target;
    });

    self.settingsViewModel.getFilteredMetadataList = ko.pureComputed(function () {
      return ko.utils.arrayFilter(self.settingsViewModel.settings.plugins.SlicerEstimator.metadata_list(), function (rec) {
        let return_value;
        return_value = (self.settingsViewModel.filterTable().length == 0 || rec.id().toLowerCase().includes(self.settingsViewModel.filterTable().toLowerCase()) || rec.description().toLowerCase().includes(self.settingsViewModel.filterTable().toLowerCase()));
        return return_value;
      });
    });


    //Settings Report Bug
    self.settingsViewModel.createIssue = function () {
      // Send the bug report
      url = 'https://github.com/NilsRo/OctoPrint-SlicerEstimator/issues/new';
      var body = "## Description\n\n**ENTER DESCRIPTION HERE\n\nDescribe your problem?\nWhat is the problem?\nCan you recreate it?\nDid you try disabling plugins?\nWhat slicer are you using?\nDid you uploaded the GCODE file causing the issue?\nDid you remember to update the subject?**\n\n\n**Plugins installed**\n";

      // Get plugin info
      OctoPrint.coreui.viewmodels.pluginManagerViewModel.plugins.allItems.forEach(function (item) {
        if (item.enabled && item.bundled == false) {
          var version = "";
          if (item.version != null) {
            version = " v" + item.version;
          }
          body += '- ' + item.name + "[" + item.key + "]" + version + "\n";
        }
      });

      // Settings
      body += "\n\n**Settings**\n";
      Object.entries(self.settingsViewModel.settings.plugins.SlicerEstimator).forEach(function (item) {
        if (item[0] == 'metadata_list') {
          body += '- ' + item[0] + ": ";
          item[1]().forEach(function (meta_item) {
            body += ' (id: ' + meta_item["id"]();
            body += ', description: ' + meta_item["description"]() + ')';
          });
          body += "\n";
        } else if (item[0] == 'plugins') {
          body += 'Installed plugins: '
          Object.entries(item[1]).forEach(function (plugin) {
            body += '(' + plugin[0] + ')'
          })
          body += "\n";
        } else {
          body += '- ' + item[0] + ": " + item[1]() + "\n";
        }

      });
      body += "\n\n**Software versions**\n- " + $('#footer_version li').map(function () { return $(this).text() }).get().join("\n- ");
      body += "\n\n\n**Browser**\n- " + navigator.userAgent
      window.open(url + '?body=' + encodeURIComponent(body));
    };
  }


  OCTOPRINT_VIEWMODELS.push({
    construct: slicerEstimatorViewModel,
    dependencies: ["printerStateViewModel", "filesViewModel", "settingsViewModel"],
    elements: ['#metadata_list', '#filamentChange_list', '#metadataStored_group']
  });
});