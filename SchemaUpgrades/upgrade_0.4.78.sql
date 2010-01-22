use beaker;
# key is a reserved word, rename to key_
alter table beaker.key rename beaker.key_;
# MySQL doesn't support unique keys larger than 768 bytes. shorten the key_name column.
alter table key_ change key_name key_name varchar(50);
