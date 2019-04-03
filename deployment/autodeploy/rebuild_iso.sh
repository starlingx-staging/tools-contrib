
ISO=$1
NEWISO=$2

sudo mount -o loop $ISO /mnt
rm -rf isolinux
mkdir isolinux
cp -rf /mnt/* isolinux/
cp /mnt/.discinfo isolinux/

echo "Modifying ISO to auto-install Standard controller with serial console and security_profile=standard"
sed -i -e "s,timeout 0,timeout 1\ndefault 0," \
    isolinux/isolinux.cfg

sed -i 's/chage -d 0 wrsroot/#chage -d 0 wrsroot/g' `grep "chage -d 0 wrsroot" ./isolinux/ -rl `
#sed -i -e "s,chage -d 0 wrsroot,#chage -d 0 wrsroot," \
#    isolinux/ks.cfg

sed -i '/Build networking scripts/ r test_controller0_network.txt' ./isolinux/smallsystem_ks.cfg
sed -i '/Build networking scripts/ r test_controller0_network.txt' ./isolinux/ks.cfg

mkisofs -o $NEWISO \
  -R -D -A 'oe_iso_boot' -V 'oe_iso_boot' \
  -quiet \
  -b isolinux.bin -c boot.cat -no-emul-boot \
  -boot-load-size 4 -boot-info-table \
  -eltorito-alt-boot \
  -e images/efiboot.img \
        -no-emul-boot \
  isolinux/

sudo umount /mnt
