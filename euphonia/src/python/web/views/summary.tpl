<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Customer</th>
                        <th>Failure Count</th>
                        <th>Failed Tests</th>
                    </tr>
                </thead>
                % for group in groups:
                   <tr>
                       <td><a href="/group/{{group['GroupId']}}">{{group['GroupName']}}</a></td>
                       <td><span popover-placement="bottom" popover-html="On the Bottom!" popover-trigger="mouseenter">{{group['numFailedTests']}}</span></td>
                       <td>
                           % for test in group['failedTests']:
                           {{test}}&nbsp;
                           %end
                       </td>
                   </tr>
                % end
            </table>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-12 text-center">
            <ul class="pagination">
                % back = ""
                % if page == 1:
                %   back = "disabled"
                % end
                % prevPage = page - 1
                % next = ""
                % if page == count:
                %   next = "disabled"
                % end
                % nextPage = page + 1
                <li class="{{back}}"><a href="/{{prevPage}}">&laquo;</a></li>
                % for i in range(1,11):
                %   pClass = ""
                %   if i == page:
                %       pClass = "active"
                %   end
                    <li class="{{pClass}}"><a href="/{{i}}">{{i}}</a></li>
                % end
                <li class=""><a href="/{{nextPage}}">&raquo;</a></li>
            </ul>
        </div>
    </div>
</div>