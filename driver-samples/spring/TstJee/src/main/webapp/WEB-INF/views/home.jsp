<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<%@ page session="false" %>
<html>
<head>
	<title>Home</title>
</head>
<body>
<h1>
	Hello world!  
</h1>

	<P>New object: ${newObj}</P>
	<c:forEach items="${objects}" var="obj">
		<c:out value="${obj} "></c:out>
		<br />
	</c:forEach>

</body>
</html>
