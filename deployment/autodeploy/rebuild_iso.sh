
set -e

INSTALL_LABEL=$1
ISO=$2
NEWISO=$3
TEST_FOLDER=$4

if [ ! -e $TEST_FOLDER/mnt ]; then
  mkdir $TEST_FOLDER/mnt
fi
if [ ! -e $TEST_FOLDER/isolinux ]; then
  mkdir $TEST_FOLDER/isolinux
else
  sudo rm -rf $TEST_FOLDER/isolinux
fi

sudo mount -o loop $ISO $TEST_FOLDER/mnt
cp -rf $TEST_FOLDER/mnt/* $TEST_FOLDER/isolinux/
cp $TEST_FOLDER/mnt/.discinfo $TEST_FOLDER/isolinux/

echo "Modifying ISO to auto-install Standard controller with serial console and security_profile=standard"
sed -i -e "s,timeout 0,timeout 1\ndefault $INSTALL_LABEL," \
    $TEST_FOLDER/isolinux/isolinux.cfg

sed -i 's/chage -d 0 sysadmin/#chage -d 0 sysadmin/g' `grep "chage -d 0 sysadmin" $TEST_FOLDER/isolinux/ -rl `
#sed -i -e "s,chage -d 0 wrsroot,#chage -d 0 wrsroot," \
#    $TEST_FOLDER/isolinux/ks.cfg

sed -i '/Build networking scripts/ r test_controller0_network.txt' $TEST_FOLDER/isolinux/smallsystem_ks.cfg
sed -i '/Build networking scripts/ r test_controller0_network.txt' $TEST_FOLDER/isolinux/smallsystem_lowlatency_ks.cfg
sed -i '/Build networking scripts/ r test_controller0_network.txt' $TEST_FOLDER/isolinux/ks.cfg
sed -i '/Build networking scripts/ r test_controller0_network.txt' $TEST_FOLDER/isolinux/pxeboot/pxeboot_smallsystem.cfg
sed -i '/Build networking scripts/ r test_controller0_network.txt' $TEST_FOLDER/isolinux/pxeboot/pxeboot_controller.cfg
sed -i '/Build networking scripts/ r test_controller0_network.txt' $TEST_FOLDER/isolinux/pxeboot/pxeboot_smallsystem_lowlatency.cfg

mkisofs -o $NEWISO \
  -R -D -A 'oe_iso_boot' -V 'oe_iso_boot' \
  -quiet \
  -b isolinux.bin -c boot.cat -no-emul-boot \
  -boot-load-size 4 -boot-info-table \
  -eltorito-alt-boot \
  -e images/efiboot.img \
        -no-emul-boot \
  $TEST_FOLDER/isolinux/

sudo umount $TEST_FOLDER/mnt
rm -rf $TEST_FOLDER/isolinux

