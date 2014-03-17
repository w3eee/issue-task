-- create database hqerp default character set utf8mb4;

use hqerp;
-- 用户系统
drop table if exists `user`;
create table `user` (
  id INTEGER NOT NULL AUTO_INCREMENT,
  email VARCHAR(64),
  pwd varchar(64),
  name varchar(64),
  status tinyint default 1,
  admin bool default 0,
  avatar varchar(64),  -- by id to created
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  primary key(id)
) engine=InnoDB;


-- 任务表
DROP TABLE IF EXISTS task;
CREATE TABLE task (
    id INTEGER NOT NULL AUTO_INCREMENT,
    project_id integer,
    title VARCHAR(128),
    `type` integer,
    status integer,
    priority integer,
    `desc` TEXT,
    created TIMESTAMP default '0000-00-00 00:00:00',
    updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires datetime,
    creator_id INTEGER,
    creator_name VARCHAR(64),
    assigned_id INTEGER,
    assigned_name VARCHAR(64),
    assigneds VARCHAR(512) COMMENT '指派用户组成的数组, json, 字典存储用户信息',
    PRIMARY KEY (id)
) engine=InnoDB;


-- 关注任务
drop table if exists task_focus;
create table task_focus (
  id INTEGER NOT NULL AUTO_INCREMENT,
  task_id INTEGER,
  task_title varchar(128),
  project_id integer,
  project_name varchar(64),
  user_id integer,
  user_name varchar(64),
  status tinyint default 1,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  primary key(id)
) engine=InnoDB;


-- 任务修改历史
DROP TABLE IF EXISTS task_log;
CREATE TABLE task_log (
    id INTEGER NOT NULL AUTO_INCREMENT,
    task_id INTEGER,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `desc` TEXT,
    note TEXT,
    updater_id INTEGER,
    updater_name VARCHAR(64),
    PRIMARY KEY (id)
) engine=InnoDB;


-- 评论表
drop table if exists comment;
create table comment (
  id integer not null auto_increment,
  from_user_id integer,
  from_user_name varchar(64),
  to_user_id integer, -- default task creator
  to_user_name varchar(64),
  task_id integer,
  task_title varchar(128),
  content text,
  `type` integer,
  parent integer default 0,
  created timestamp DEFAULT CURRENT_TIMESTAMP,
  primary key(id)
) engine=InnoDB;


-- 通知系统, 私信支持
drop table if exists message;
create table message (
  id integer not null auto_increment,
  user_id integer,
  `type` integer,
  from_user_id integer,
  from_user_name varchar(64),
  content text,
  project_id integer,
  project_name varchar(64),
  task_id integer,
  task_title varchar(128),
  status tinyint default 1,
  created timestamp DEFAULT CURRENT_TIMESTAMP,
  primary key(id)
) engine=InnoDB;


-- 项目系统
drop table if exists project;
create table project (
  id integer not null auto_increment,
  name varchar(64),
  created timestamp DEFAULT CURRENT_TIMESTAMP,
  note text,
  status tinyint default 2,
  primary key(id)
) engine=InnoDB;


-- 权限控制
drop table if exists auth;
create table auth (
  id integer not null auto_increment,
  project_id integer,
  project_name varchar(64),
  user_id integer,
  user_name varchar(64),
  status tinyint default 1,
  primary key(id)
) engine=InnoDB;


-- key重复检测表
drop table if exists gen_key;
create table gen_key (
  `key` varchar(64),
  num integer,
  primary key(`key`)
) engine=InnoDB;


-- todo
-- file
drop table if exists file;
create table file (
  id integer not null auto_increment,
  xid varchar(64),
  name varchar(32),
  `type` varchar(16),
  status tinyint default 1,
  fs_path varchar(64),
  created timestamp DEFAULT CURRENT_TIMESTAMP,
  primary key(id)
) engine=InnoDB;
