### TODO list
1) Improve documentation
2) Automatize Outlook-notification sending
3) Generate separate patching list for service owners
4) Parallel the ssh-connection
5) Fix bug when autonotification e-mail is not created for servers which not require MM
6) Add parse-config option
7) Add logrotate for scripts

### Solution for automatize several steps in patching process
Hi, I am working as Linux engeneer and we have several hundred Linux-servers in our scope. We have a ugly patching process in our IT-infrastructure. And this scripts have been wrote for particilary automatize patching process. 
Perhaps you will ask 'why your patching approach so strange?'. I can not answered for you, because we are working with ITIL and must follow strange and non-optimal processess. We can not influence to this process. Also our managers are terrible and do not have a it-knowledge and they are thinking that all fine... 

#### So, listen, common aproach, basic rules:
1) Every our server have a patching time and patching day
2) Patching day -- day of the week in month (for example, first Monday in monthh, third Sunday and etc.)
3) We have patching codes for patching days
4) Every server aso have a patching time (Second Monday between 16:00-20:00 CET)

#### Our infrastructure:
1) We are using [salt](https://github.com/saltstack/salt) for automatize our work
2) Our virtual servers work on VmWare
3) We have CentOS, RedHat, Debian and Open Suse distr

#### Our patching approach (our amazing processes)
1) On one day of the month we must collect the patching list (list of updates which will be installed on servers) for future Patching cycle. We collect this report once per month. Honestly we do not use the ‘repo freeze’ and our patching report can be non-relevant even today if new patches will be released… But nobody care regarding to this, it is only formal thing
2) After that this list send to SO (service owners) to review (they should investigate this list with application support team and decide which patches can affect the application stability and should be excluded from patching). But during 2 year we did not receive any feedback from service owners, but nobody care regarding to this
3) During collection of patching list also csv-files are created which used for schedule maintenance mode in monitoring system (avoid unnecessary incidents), csv-files which used for send e-mail notification before 15 min. patching process, create snapshots and etc. This section will be considered later
4) We schedule maintenance mode in check-mk for affected servers (avoid unnecessary servers) once per month via special script on check-mk server side and csv-files
5) Before 15 min. to patching every service owners and application support team receive an e-mail notification such as:
*‘Dear [name],
Please be informed that patching of [server_name] server will be started at [time] CET’*
6) Before 5 min. other script create snapshot of the virtual servers via [salt-cloud](https://docs.saltstack.com/en/latest/topics/cloud/vmware.html#configuration) solution
7) And patching performed manually [yes, manual patching in 2018(!), my company is not modern]. Once patching completed we send the notification to service owner manually (reply to e-mail from point 5)



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
