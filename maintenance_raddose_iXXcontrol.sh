export uid=$(/usr/bin/id -u)

echo "#########"
/usr/bin/date
/usr/bin/hostname
echo "+++++++++"
if  [ ! -d  /run/user/${uid}/raddose3d/cache/ ];then
    echo "FOlder did not exist. Creating"
    mkdir -p /run/user/${uid}/raddose3d/cache/
fi

/usr/bin/du -hsc /run/user/${uid}/raddose3d/cache
free_space=$(/usr/bin/df -k /run/user/${uid}/raddose3d/cache/ --output=pcent|tail -1|cut -d"%" -f1)
echo "Free space: $free_space %"
if (( ${free_space} < 10 ));then
    echo "Deleting less agressively days"
    /usr/bin/find /run/user/${uid}/raddose3d/cache -type d -mtime +2 -not -path "/run/user/1007182/raddose3d/cache" -exec rm -rf {} \;
elif (( ${free_space} < 25 ));then
    echo "Deleting less agressively hours"
    /usr/bin/find /run/user/${uid}/raddose3d/cache -type d -mmin +60 -not -path "/run/user/1007182/raddose3d/cache" -exec rm -rf {} \;
elif (( ${free_space} < 50 ));then
    echo "Deleting more agressively tens of minutes"
    /usr/bin/find /run/user/${uid}/raddose3d/cache -type d -mmin +30 -not -path "/run/user/1007182/raddose3d/cache" -exec rm -rf {} \;
elif (( ${free_space} < 75 ));then
    echo "Deleting more agressively 5 minutes"
    /usr/bin/find /run/user/${uid}/raddose3d/cache -type d -mmin +5 -not -path "/run/user/1007182/raddose3d/cache" -exec rm -rf {} \;
elif (( ${free_space} < 90 ));then
    echo "Deleting more agressively one minute"
    /usr/bin/find /run/user/${uid}/raddose3d/cache -type d -mmin +1 -not -path "/run/user/1007182/raddose3d/cache" -exec rm -rf {} \;
fi

if  [ ! -d  /run/user/${uid}/raddose3d/cache/ ];then
    echo "Folder did not exist. Creating"
    mkdir -p /run/user/${uid}/raddose3d/cache/
fi

/usr/bin/du -hsc /run/user/${uid}/raddose3d/cache
echo "########"
