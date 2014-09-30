<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            <h1 class="page-header">Support Issue Workflows</h1>
        </div>
    </div>
    % windex = 0
    % for workflow in workflows:
    % include('workflow', workflows=workflows, workflow=workflow, windex=windex)
    % windex = windex + 1
    % end
</div>