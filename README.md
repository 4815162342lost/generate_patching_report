### Get list of all available updates of the packages on Linux!

Simple Python 3 program for collect patching list (get upgradeable packages) and save results to Excel (xlsx) format.

Require [salt](https://github.com/saltstack/salt)

Tested on CentOS 7.3, Oracle Linux 7.1, Debian 8. I am using the program on production environment more than 5 months.

The result writes to xslx format:
Total sheet -- the common results. You can see:
1) All servers
2) Conclusion -- how many packages need upgrade
3) Need kernel update or not
3) Reboot require or not. Depends on the packages: "glibc", "hal", "systemd", "udev", "kernel*", "linux-image*". You can edit tuple packages_which_require_reboot, if you want
4) You can exclude some potential risky packages from patching (edit yum.conf for example). You can make sure that all 'bad packages' excluded from patching, edit tuple bad_packages
Also, you can see simple chart and Totals in list.
![alt text](https://github.com/4815162342lost/get_all_updates_list_via_salt/blob/master/screenshots/Screenshot%20from%202017-07-10%2000-00-44.png)

As well every server has a own sheet with upgradeable list:
You can found package name, which can upgrade, current and new available version.
![alt text](https://github.com/4815162342lost/get_all_updates_list_via_salt/blob/master/screenshots/Screenshot%20from%202017-07-10%2000-01-02.png)

See [**Aug_full_patches.xlsx**](https://github.com/4815162342lost/get_all_updates_list_via_salt/blob/master/screenshots/Aug_full_patches.xlsx?raw=true)  for more examples.


Instructions:
- change the current directory to script placement dir
- edit server_list.txt file
- run program via sudo ./main.py

Also you can send results via e-mail.
You should:
1) Replace "from" e-mail address if you want in main.py:
msg['From'] = "me"
2) Replace smtp address in main.py:
s = smtplib.SMTP("smtp.my_organization.net")
3) Run the program with '-c' option:
sudo ./main.py -c 'my_addreess@my_domain.com'

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
