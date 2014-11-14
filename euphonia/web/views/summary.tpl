<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Customer</th>
                        <th>Failure Count</th>
                        <th>Priority</th>
                    </tr>
                </thead>
                % for group in groups:
                   <tr>
                       <td><a href="/group/{{group['GroupId']}}">{{group['GroupName']}}</a></td>
                       % failedTestsContent = "<ul>"
                       % for test in group['failedTests']:
                       %    testText = ''.join(["<li>",test['test'],"</li>"])
                       %    if test['test'] == issue:
                       %        testText = ''.join(['<li style="color:#ff0000;"><b>',test['test'],'</b></li>'])
                       %    end
                       %    failedTestsContent = failedTestsContent + testText
                       % end
                       % failedTestsContent = failedTestsContent + "</ul>"
                       <td><span class="failedtests" data-toggle="popover" data-trigger="hover" data-placement="right" data-html="true" title="<b>Failed Tests</b>" data-content="{{failedTestsContent}}">{{group['numFailedTests']}}</span></td>
                       <td><b>{{group['priority']}}</b></td>
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
                <li class="{{back}}"><a href="/groups/page/{{prevPage}}">&laquo;</a></li>
                % for i in range(1,11):
                %   pClass = ""
                %   if i == page:
                %       pClass = "active"
                %   end
                    <li class="{{pClass}}"><a href="/groups/page/{{i}}">{{i}}</a></li>
                % end
                <li class=""><a href="/groups/page/{{nextPage}}">&raquo;</a></li>
            </ul>
        </div>
    </div>
</div>