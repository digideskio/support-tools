<%
class_done = ""
class_frozen = ""
style_done = ""
style_frozen = ""
if task['done'] == True:
    class_done = "done"
    if hide_done == True:
        style_done = "display:none;"
    end
end
if task['frozen'] == True:
    class_frozen = "frozen"
    if hide_frozen == True:
        style_frozen = "display:none;"
    end
end
%>
<tr id="{{task['_id']}}" class="tr_task {{class_done}} {{class_frozen}}" style="height:2em;{{style_done}};{{style_frozen}}">
    <td style="width:5%"><input id="checkbox_{{task['_id']}}" name="taskIds[]" type="checkbox" value="{{task['_id']}}"></td>
    <td style="width:30%"><a href="javascript:void(0);" onclick="showPage(this,'http://jira.mongodb.org/browse/{{issue['key']}}','{{issue['key']}}');">{{issue['key']}}</a></td>
    <td style="width:30%" class="startdate">{{task['startDate']}}</td>
    <td style="width:35%">
        <i id="{{task['_id']}}-time" class="glyphicon glyphicon-time metadata" data-toggle="tooltip" data-placement="top" title="Last Updated: {{task['updateDate']}}"></i>
        <%
            if 'frozen' in task and task['frozen'] == True:
                hidden = ""
            else:
                hidden = "display:none"
            end
        %>
        <i id="{{task['_id']}}-frozen" class="glyphicon glyphicon-certificate metadata stats" style="{{hidden}}" data-toggle="tooltip" data-placement="top" title="Frozen"></i>
        <%
            if task['done'] == True:
                hidden = ""
            else:
                hidden = "display:none"
            end
        %>
        <i id="{{task['_id']}}-done" class="glyphicon glyphicon-ok metadata stats" style="{{hidden}}" data-toggle="tooltip" data-placement="top" title="Done"></i>
        <%
            if task['inProg'] == True:
                hidden = ""
            else:
                hidden = "display:none"
            end
        %>
        <i id="{{task['_id']}}-inprogress" class="glyphicon glyphicon-refresh metadata stats" style="{{hidden}}" data-toggle="tooltip" data-placement="top" title="In Progress"></i>
        <%
            if task['approved'] == True and task['done'] == False:
                hidden = ""
            else:
                hidden = "display:none"
            end
        %>
        <i id="{{task['_id']}}-approve" class="glyphicon glyphicon-thumbs-up metadata stats" style="{{hidden}}" data-toggle="tooltip" data-placement="top" title="Approved, not Done"></i>
    </td>
</tr>
