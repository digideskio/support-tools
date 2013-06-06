# PHP driver

## Install driver

[PHP: Installation - Manual](http://www.php.net/manual/en/mongo.installation.php#mongo.installation.osx)

## php-find.php

This connects to localhost, does an insert on `test.items`, a find and then print.

To run this on CLI:

	php php-find.php

Sample output:

	$ php php-find.php
	1 document inserted
	1 document(s) found.
	Title: Calvin and Hobbes
	Author: Bill Watterson
	Published: 2012-09-19 03:47:44
	test.items dropped