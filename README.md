### Solution for automatize several steps in patching process
Hi, I am working as Linux engeneer and we have several hundred Linux-servers in our scope. We have a ugly patching process in our IT-infrastructure. And this scripts have been wrote for particilary automatize patching process. 
Perhaps you will ask 'why your patching approach so strange?'. I can not answered for you, because we are working with ITIL and must follow strange and non-optimal processess. We can not influence to this process.

#### So, listen, common aproach, basic rules:
1) Every our server have a patching time and patching day
2) Patching day -- day of the week in month (for example, first Monday in monthh, third Sunday and etc)
3) We have patching codes for patching date
4) Every server aso have a patching time (Second Monday 16:00-20:00)

#### Our infrastructure:
1) We are using [salt](https://github.com/saltstack/salt) for automatize our work
2) Our virtual servers work on VmWare
3) We have CentOS, RedHat, Debian and Open Suse distr

#### Our patching approach (our amazing processes)
1) 

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
