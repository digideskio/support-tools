<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            <h1 class="page-header">Upload Files</h1>
        </div>
    </div>
    <div id="actions" class="row">

      <div class="col-lg-7">
        <!-- The fileinput-button span is used to style the file input field as button -->
        <span class="btn btn-success fileinput-button dz-clickable">
            <i class="glyphicon glyphicon-plus"></i>
            <span>Add files...</span>
        </span>
        <button type="submit" class="btn btn-primary start">
            <i class="glyphicon glyphicon-upload"></i>
            <span>Start upload</span>
        </button>
        <button type="reset" class="btn btn-warning cancel">
            <i class="glyphicon glyphicon-ban-circle"></i>
            <span>Cancel upload</span>
        </button>
      </div>

      <div class="col-lg-5">
        <!-- The global file processing state -->
        <span class="fileupload-process">
          <div id="total-progress" class="progress progress-striped active" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" style="opacity: 0;">
            <div class="progress-bar progress-bar-success" style="width: 100%;" data-dz-uploadprogress=""></div>
          </div>
        </span>
      </div>

    </div>
    <div class="row">
        <div class="table table-striped files" id="previews">
            <div id="template" class="file-row">
            <!-- This is used as the file preview template -->
                <div class="col-lg-1">
                    <span class="preview"><img data-dz-thumbnail /></span>
                </div>
                <div class="col-lg-4">
                    <p class="name col-lg-9" data-dz-name></p>
                    <span class="col-lg-3">
                        <select name="category">
                            <option></option>
                            <option value="mdiag">mdiag report</option>
                            <option value="group_report">group report</option>
                        </select>
                    </span>
                    <strong class="error text-danger" data-dz-errormessage></strong>
                </div>
                <div class="col-lg-4">
                    <p class="size" data-dz-size></p>
                    <div class="progress progress-striped active" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
                        <div class="progress-bar progress-bar-success" style="width:0%;" data-dz-uploadprogress></div>
                    </div>
                </div>
                <div class="col-lg-2">
                    <button class="btn btn-primary start">
                        <i class="glyphicon glyphicon-upload"></i>
                        <span>Start</span>
                    </button>
                    <button data-dz-remove class="btn btn-warning cancel">
                        <i class="glyphicon glyphicon-ban-circle"></i>
                        <span>Cancel</span>
                    </button>
                    <button data-dz-remove class="btn btn-danger delete">
                        <i class="glyphicon glyphicon-trash"></i>
                        <span>Delete</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>