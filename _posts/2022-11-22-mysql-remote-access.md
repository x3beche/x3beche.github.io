---
layout: post
title: How to give remote access for all hosts in MySQL
description: How to give remote access for all hosts in MySQL
summary: How to give remote access for all hosts in MySQL
tags: mysql remote access
minute: 5
---

As mentioned in the comments, since MySql 8 you need to first explicitly create the user, so the command will look like:

    CREATE USER 'root'@'%' IDENTIFIED BY 'password'; GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;

**Original answer:**

There's two steps in that process:

a) Grant privileges. As root user execute with this substituting `'password'` with your current root password :

    GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY 'password';

b) bind to all addresses:

The easiest way is to **comment out** the line in your `my.cnf` file:

    #bind-address = 127.0.0.1 

and restart mysql

    service mysql restart

By default it binds only to localhost, but if you comment the line it binds to all interfaces it finds. Commenting out the line is equivalent to `bind-address=*`.

To check where mysql service has binded execute as root:


    netstat -tupan | grep mysql


**Update For Ubuntu 16:**

Config file is (now) 

    /etc/mysql/mysql.conf.d/mysqld.cnf 

(at least on standard Ubuntu 16)
