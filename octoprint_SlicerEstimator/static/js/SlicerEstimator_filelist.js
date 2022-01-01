/*
 * View model for OctoPrint-SlicerEstimator_filelist
*/

$(function() {
  function slicerFilesViewModel(parameters) {
    var self = this;
    self.filesViewModel = parameters[0];
    
    // Overwrite the printTimeLeftOriginClass function
    self.getSlicerAdditionalData = function(data) {
      let result = ko.pureComputed(function() {
        let value = self.filesViewModel.getAdditionalData(data);
       
        alert(objToString(value));
        value += gettext("blabla<br>");
        return value;
      });
      return result;
    };

    self.filesViewModel.getAdditionalData = self.getSlicerAdditionalData;
  
  };

  function objToString (obj) {
    let str = '';
    for (const [p, val] of Object.entries(obj)) {
        str += `${p}::${val}\n`;
    }
    return str;
  };

  /* view model class, parameters for constructor, container to bind to
   * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
   * and a full list of the available options.
   */
  OCTOPRINT_VIEWMODELS.push({
    construct: slicerFilesViewModel,
    dependencies: ["filesViewModel"]
  });
});