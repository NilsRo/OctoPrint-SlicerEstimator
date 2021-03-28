/*
 * View model for OctoPrint-SlicerEstimator
*/

$(function() {
  function slicerEstimatorViewModel(parameters) {
    var self = this;

    self.printerStateViewModel = parameters[0];
    
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
  }
  /* view model class, parameters for constructor, container to bind to
   * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
   * and a full list of the available options.
   */
  OCTOPRINT_VIEWMODELS.push({
    construct: slicerEstimatorViewModel,
    dependencies: ["printerStateViewModel"]
  });
});