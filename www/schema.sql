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

