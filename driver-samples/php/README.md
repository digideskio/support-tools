# PHP driver

## Install driver

[PHP: Installation - Manual](http://www.php.net/manual/en/mongo.installation.php#mongo.installation.osx)

## php-crud.php

PHP crud - Create, read, update and delete

This example connects to localhost, insert a document in `test.items`, finds it and then print.
Lastly it drops the `items` collection.

Run this:

	$ php php-find.php

Sample output:

	php mongodb driver version 1.5.4
	1 document inserted
	1 document(s) found.
	Title: Calvin and Hobbes
	Author: Bill Watterson
	Published: 2012-09-19 03:47:44
	test.items dropped