DROP DATABASE IF EXISTS awesome;

CREATE DATABASE awesome;

USE awesome;

GRANT SELECT,INSERT,UPDATE,DELETE ON awesome.* to 'www-data'@'localhost' identified by 'www-data';

CREATE TABLE users(
  `id` VARCHAR(50) NOT NULL,
  `email` VARCHAR(50) NOT NULL,
  `passwd` VARCHAR(50) NOT NULL,
  `admin` BOOL NOT NULL,
  `name` VARCHAR(50) NOT NULL ,
  `image` VARCHAR(500) NOT NULL,
  `created_at` REAL NOT NULL,
  UNIQUE KEY `idx_email` (`email`),
  KEY `idx_created_at`(`created_at`),
  PRIMARY KEY (`id`)
)engine=innodb default charset=utf8;

create table blogs (
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `name` varchar(50) not null,
    `summary` varchar(200) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

create table comments (
    `id` varchar(50) not null,
    `blog_id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `user_name` varchar(50) not null,
    `user_image` varchar(500) not null,
    `content` mediumtext not null,
    `created_at` real not null,
    key `idx_created_at` (`created_at`),
    primary key (`id`)
) engine=innodb default charset=utf8;

CREATE TABLE `history_read` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `novelname` varchar(50) NOT NULL,
  `openid` varchar(200) NOT NULL,
  `last_read_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `chapter_url` varchar(200) NOT NULL,
  `chapter_name` varchar(200) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=82362 DEFAULT CHARSET=utf8;

CREATE TABLE `wx_form_id` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `openid` varchar(100) NOT NULL,
  `form_id` varchar(100) NOT NULL,
  `status` int(2) DEFAULT '0',
  `created_time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_push` int(2) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=82360 DEFAULT CHARSET=utf8;NGINE=InnoDB AUTO_INCREMENT=82360 DEFAULT CHARSET=utf8;

CREATE TABLE `wx_push` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `push_url` varchar(256) DEFAULT '""',
  `openid` varchar(100) DEFAULT '""',
  `novel_name` varchar(256) DEFAULT '""',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8;