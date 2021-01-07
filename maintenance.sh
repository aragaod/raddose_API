echo "#########"
/usr/bin/date
/usr/bin/hostname
echo "+++++++++"
/usr/bin/du -hsc /run/user/1007182/raddose3d/cache
free_space=$(/usr/bin/df -k /run/user/1007182/raddose3d/cache/ --output=pcent|tail -1|cut -d"%" -f1)
echo "Free space: $free_space %"
if (( ${free_space} < 10 ));then
    echo "Deleting less agressively days"
    /usr/bin/find /run/user/1007182/raddose3d/cache -mtime +2 -exec rm -rf {} \;
elif (( ${free_space} < 25 ));then
    echo "Deleting less agressively hours"
    /usr/bin/find /run/user/1007182/raddose3d/cache -mmin +60 -exec rm -rf {} \;
elif (( ${free_space} < 50 ));then
    echo "Deleting more agressively tens of minutes"
    /usr/bin/find /run/user/1007182/raddose3d/cache -mmin +30 -exec rm -rf {} \;
elif (( ${free_space} < 75 ));then
    echo "Deleting more agressively 5 minutes"
    /usr/bin/find /run/user/1007182/raddose3d/cache -mmin +5 -exec rm -rf {} \;
elif (( ${free_space} < 90 ));then
    echo "Deleting more agressively one minute"
    /usr/bin/find /run/user/1007182/raddose3d/cache -mmin +1 -exec rm -rf {} \;
fi
/usr/bin/du -hsc /run/user/1007182/raddose3d/cache
echo "########"
