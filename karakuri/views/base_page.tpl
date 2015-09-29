<!DOCTYPE html>

<html lang="en">
    % include('head.tpl')
    <body>
        <%
        include('nav.tpl')
        if defined('renderpage'):
            include(renderpage)
        end
        include('footer.tpl')
        %>
    </body>
</html>