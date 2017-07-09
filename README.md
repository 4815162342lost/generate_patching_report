### Get list of all available updates of the packages on Linux!

Get upgradable packages list on Linux and save list to xlsx file.

Python3-program for get all updates from the servers via [salt](https://github.com/saltstack/salt)

Tested on CentOS 7.3, Oracle Linux 7.1, Debian 8.

The result writes to xslx format:
![alt text](https://github.com/4815162342lost/get_all_updates_list_via_salt/blob/master/screenshots/Screenshot%20from%202017-07-10%2000-00-44.png)
![alt text](https://github.com/4815162342lost/get_all_updates_list_via_salt/blob/master/screenshots/Screenshot%20from%202017-07-10%2000-01-02.png)

See [**Aug_full_patches.xlsx**](https://github.com/4815162342lost/get_all_updates_list_via_salt/blob/master/screenshots/Aug_full_patches.xlsx)  for more examples.


Instructions:
- change the current directory to script placement dir
- edit server_list.txt file
- run program via sudo ./main.py

Example:
```
vodka@vodka-PC: cd ~/PycharmProjects/get_list_of_all_updates/
vodka@vodka-PC:~/PycharmProjects/get_list_of_all_updates$ sudo ./main.py 
[sudo] password for vodka: 
Hello! Nice to meet you!
, // ,,/ ,.// ,/ ,// / /, // ,/, /, // ,/,
/, // ,/,_|_// ,/ ,, ,/, // ,/ /, //, /,/
 /, /,.-'   '-. ,// ////, // ,/,/, // ///
, ,/,/         \ // ,,///, // ,/,/, // ,
,/ , ^^^^^|^^^^^ ,// ///  /,,/,/, ///, //
 / //     |  O    , // ,/, //, ///, // ,/
,/ ,,     J\/|\_ |+'(` , |) ^ ||\|||\|/` |
 /,/         |   || ,)// |\/-\|| ||| |\] .
/ /,,       /|    . ,  ///, . /, // ,//, /
, / /,/     \ \    ). //, ,( ,/,/, // ,/,

Starting the collect of all patches on the servers from server_list.txt file...
All done. Please, see the file Jun_full_patches.xlsx. Have a nice day!```
