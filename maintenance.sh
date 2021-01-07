echo "#########"
/usr/bin/date
/usr/bin/hostname
echo "+++++++++"
/usr/bin/du -hsc /run/user/1007182/raddose3d/
/usr/bin/find /run/user/1007182/raddose3d/ -mtime +1 -exec rm -rf {} \;
/usr/bin/du -hsc /run/user/1007182/raddose3d/
echo "########"
