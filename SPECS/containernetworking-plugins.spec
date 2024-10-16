%global with_check 0

%if ! 0%{?gobuild:1}
%define gobuild(o:) \
go build -buildmode pie -compiler gc -tags="rpm_crashtraceback ${BUILDTAGS:-}" -ldflags "${LDFLAGS:-} -linkmode=external -compressdwarf=false -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n') -extldflags '%__global_ldflags'" -a -v %{?**};
%define gotest(o:) go test
%endif

%global provider github
%global provider_tld com
%global project containernetworking
%global repo plugins
# https://github.com/containernetworking/plugins
%global provider_prefix %{provider}.%{provider_tld}/%{project}/%{repo}
%global import_path %{provider_prefix}

Epoch: 1
Name: containernetworking-plugins
Version: 1.4.0
Release: 6%{?dist}
Summary: CNI network plugins
License: ASL 2.0
URL: https://%{provider_prefix}
Source0: https://%{provider_prefix}/archive/v%{version}.tar.gz
# https://fedoraproject.org/wiki/PackagingDrafts/Go#Go_Language_Architectures
ExclusiveArch: %{go_arches}
BuildRequires: golang >= 1.16.6
BuildRequires: git
BuildRequires: /usr/bin/go-md2man
BuildRequires: systemd-devel
Requires: systemd
Provides: containernetworking-cni = %{epoch}:%{version}-%{release}

%description
The CNI (Container Network Interface) project consists of a specification
and libraries for writing plugins to configure network interfaces in Linux
containers, along with a number of supported plugins. CNI concerns itself
only with network connectivity of containers and removing allocated resources
when the container is deleted.

%prep
%autosetup -Sgit -n %{repo}-%{version}
rm -rf plugins/main/windows
sed -i 's,/opt/cni/bin/,/usr/libexec/cni/,' plugins/ipam/dhcp/systemd/cni-dhcp.service

%build
export ORG_PATH="%{provider}.%{provider_tld}/%{project}"
export REPO_PATH="$ORG_PATH/%{repo}"

if [ ! -h gopath/src/${REPO_PATH} ]; then
	mkdir -p gopath/src/${ORG_PATH}
	ln -s ../../../.. gopath/src/${REPO_PATH} || exit 255
fi

export GOPATH=$(pwd)/gopath
export GO111MODULE=off
export CGO_CFLAGS="%{optflags} -D_GNU_SOURCE -D_LARGEFILE_SOURCE -D_LARGEFILE64_SOURCE -D_FILE_OFFSET_BITS=64"
mkdir -p $(pwd)/bin

echo "Building plugins"
export PLUGINS="plugins/meta/* plugins/main/* plugins/ipam/* plugins/sample"
for d in $PLUGINS; do
	if [ -d "$d" ]; then
		plugin="$(basename "$d")"
		echo "  $plugin"
		%gobuild -o "${PWD}/bin/$plugin" "$@" "$REPO_PATH"/$d
	fi
done

%install
install -d -p %{buildroot}%{_libexecdir}/cni/
install -p -m 0755 bin/* %{buildroot}/%{_libexecdir}/cni

install -dp %{buildroot}%{_unitdir}
install -p plugins/ipam/dhcp/systemd/cni-dhcp.service %{buildroot}%{_unitdir}
install -p plugins/ipam/dhcp/systemd/cni-dhcp.socket %{buildroot}%{_unitdir}

%check
%if 0%{?with_check}
# Since we aren't packaging up the vendor directory we need to link
# back to it somehow. Hack it up so that we can add the vendor
# directory from BUILD dir as a gopath to be searched when executing
# tests from the BUILDROOT dir.
ln -s ./ ./vendor/src # ./vendor/src -> ./vendor

export GOPATH=%{buildroot}/%{gopath}:$(pwd)/vendor:%{gopath}

%gotest %{import_path}/libcni
%gotest %{import_path}/pkg/invoke
%gotest %{import_path}/pkg/ip
%gotest %{import_path}/pkg/ipam
%gotest %{import_path}/pkg/ns
%gotest %{import_path}/pkg/skel
%gotest %{import_path}/pkg/types
%gotest %{import_path}/pkg/types/020
%gotest %{import_path}/pkg/types/current
%gotest %{import_path}/pkg/utils
%gotest %{import_path}/pkg/utils/hwaddr
%gotest %{import_path}/pkg/version
%gotest %{import_path}/pkg/version/legacy_examples
%gotest %{import_path}/pkg/version/testhelpers
%gotest %{import_path}/plugins/ipam/dhcp
%gotest %{import_path}/plugins/ipam/host-local
%gotest %{import_path}/plugins/ipam/host-local/backend/allocator
%gotest %{import_path}/plugins/main/bridge
%gotest %{import_path}/plugins/main/ipvlan
%gotest %{import_path}/plugins/main/loopback
%gotest %{import_path}/plugins/main/macvlan
%gotest %{import_path}/plugins/main/ptp
%gotest %{import_path}/plugins/meta/flannel
%gotest %{import_path}/plugins/test/noop
%endif

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
%license LICENSE
%doc *.md
%dir %{_libexecdir}/cni
%{_libexecdir}/cni/*
%{_unitdir}/cni-dhcp.service
%{_unitdir}/cni-dhcp.socket

%changelog
* Tue Oct 08 2024 Jindrich Novy <jnovy@redhat.com> - 1:1.4.0-6
- rebuild for CVE-2024-34156
- Resolves: RHEL-57915

* Tue Jul 23 2024 Jindrich Novy <jnovy@redhat.com> - 1:1.4.0-5
- rebuild for CVE-2024-24783
- Resolves: RHEL-28431

* Fri Jun 21 2024 Jindrich Novy <jnovy@redhat.com> - 1:1.4.0-4
- rebuild for CVE-2024-1394
- Resolves: RHEL-40809

* Thu May 02 2024 Jindrich Novy <jnovy@redhat.com> - 1:1.4.0-3
- rebuild for CVE-2023-45290
- Resolves: RHEL-28384

* Mon Mar 04 2024 Jindrich Novy <jnovy@redhat.com> - 1:1.4.0-2
- rebuild
- Related: RHEL-18372

* Tue Jan 02 2024 Jindrich Novy <jnovy@redhat.com> - 1:1.4.0-1
- update to https://github.com/containernetworking/plugins/releases/tag/v1.4.0
- Related: RHEL-2112

* Thu Sep 14 2023 Jindrich Novy <jnovy@redhat.com> - 1:1.3.0-5
- fix path to dhcp service
- Resolves: #RHEL-3140

* Fri Aug 11 2023 Jindrich Novy <jnovy@redhat.com> - 1:1.3.0-4
- add Epoch in Provides
- Related: #2176063

* Sat Jul 08 2023 Jindrich Novy <jnovy@redhat.com> - 1:1.3.0-3
- remove no_openssl for FIPS compliance
- Related: #2176063

* Tue Jun 13 2023 Jindrich Novy <jnovy@redhat.com> - 1:1.3.0-2
- rebuild for following CVEs:
CVE-2022-41724 CVE-2022-41725 CVE-2023-24538 CVE-2023-24534 CVE-2023-24536 CVE-2022-41723 CVE-2023-24539 CVE-2023-24540 CVE-2023-29400
- Resolves: #2179960
- Resolves: #2187333
- Resolves: #2187376
- Resolves: #2203705
- Resolves: #2207519

* Thu May 11 2023 Jindrich Novy <jnovy@redhat.com> - 1:1.3.0-1
- update to https://github.com/containernetworking/plugins/releases/tag/v1.3.0
- Related: #2176063

* Tue Jan 17 2023 Jindrich Novy <jnovy@redhat.com> - 1:1.2.0-1
- update to https://github.com/containernetworking/plugins/releases/tag/v1.2.0
- Related: #2124478

* Fri May 13 2022 Jindrich Novy <jnovy@redhat.com> - 1:1.1.1-3
- Re-enable LTO and debuginfo
- Related: #2061316

* Wed May 11 2022 Jindrich Novy <jnovy@redhat.com> - 1:1.1.1-2
- BuildRequires: /usr/bin/go-md2man
- Related: #2061316


* Thu Mar 10 2022 Jindrich Novy <jnovy@redhat.com> - 1:1.1.1-1
- update to https://github.com/containernetworking/plugins/releases/tag/v1.1.1
- Related: #2061316

* Tue Mar 08 2022 Jindrich Novy <jnovy@redhat.com> - 1:1.1.0-1
- update to https://github.com/containernetworking/plugins/releases/tag/v1.1.0
- Related: #2061316

* Mon Feb 28 2022 Jindrich Novy <jnovy@redhat.com> - 1:1.0.1-4
- revert back to https://github.com/containernetworking/plugins/releases/tag/v1.0.1
- Related: #2000051

* Mon Feb 28 2022 Jindrich Novy <jnovy@redhat.com> - 1.1.0-1
- update to https://github.com/containernetworking/plugins/releases/tag/v1.1.0
- Related: #2000051

* Fri Oct 01 2021 Jindrich Novy <jnovy@redhat.com> - 1.0.1-3
- perform only sanity/installability tests for now
- Related: #2000051

* Wed Sep 29 2021 Jindrich Novy <jnovy@redhat.com> - 1.0.1-2
- add gating.yaml
- Related: #2000051

* Wed Sep 08 2021 Jindrich Novy <jnovy@redhat.com> - 1.0.1-1
- update to https://github.com/containernetworking/plugins/releases/tag/v1.0.1
- Related: #2000051

* Fri Sep 03 2021 Jindrich Novy <jnovy@redhat.com> - 1.0.0-1
- add systemd dependencies
- Related: #2000051

* Mon Aug 09 2021 Mohan Boddu <mboddu@redhat.com> - 0.9.1-4
- Rebuilt for IMA sigs, glibc 2.34, aarch64 flags
  Related: rhbz#1991688

* Tue Jun 22 2021 Mohan Boddu <mboddu@redhat.com> - 0.9.1-3
- Rebuilt for RHEL 9 BETA for openssl 3.0
  Related: rhbz#1971065

* Thu Apr 15 2021 Mohan Boddu <mboddu@redhat.com> - 0.9.1-2
- Rebuilt for RHEL 9 BETA on Apr 15th 2021. Related: rhbz#1947937

* Sat Feb 06 2021 Jindrich Novy <jnovy@redhat.com> - 0.9.1-1
- update to https://github.com/containernetworking/plugins/releases/tag/v0.9.1

* Thu Dec 10 2020 Jindrich Novy <jnovy@redhat.com> - 0.9.0-1
- update to https://github.com/containernetworking/plugins/releases/tag/v0.9.0

* Wed Dec 09 2020 Petr Šabata <contyk@redhat.com> - 0.8.7-3.1
- Bumping for the gcc-11 rebuild

* Mon Dec 07 2020 Jindrich Novy <jnovy@redhat.com> - 0.8.7-3
- use dedicated macro to build only on supported arches
- make build logs more readable
- always compile with debuginfo enabled

* Thu Nov 05 2020 Jindrich Novy <jnovy@redhat.com> - 0.8.7-2
- attempt to fix linker error with golang-1.15

* Fri Sep 18 2020 Jindrich Novy <jnovy@redhat.com> - 0.8.7-1
- update to https://github.com/containernetworking/plugins/releases/tag/v0.8.7

* Thu Sep 17 2020 Jindrich Novy <jnovy@redhat.com> - 0.8.6-2
- sync with rhel8-8.3.0

* Thu Sep 17 2020 Jindrich Novy <jnovy@redhat.com> - 0.8.6-1
- propagate proper CFLAGS to CGO_CFLAGS to assure code hardening and optimization
- Related: #1821193

* Thu Jun 13 2019 Lokesh Mandvekar <lsm5@redhat.com> - 0.8.1-1
- Resolves: #1720319 - bump to v0.8.1

* Sat Jun 01 2019 Lokesh Mandvekar <lsm5@redhat.com> - 0.7.5-1
- Resolves: #1616063
- bump to v0.7.5

* Tue Dec 18 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.4-3.git9ebe139
- re-enable debuginfo

* Mon Dec 17 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.4-2.git9ebe139
- rebase, removed patch that is already upstream

* Mon Dec 17 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.3-7.git19f2f28
- go tools not in scl anymore

* Mon Aug 27 2018 Lokesh Mandvekar <lsm5@redhat.com> - 0.7.3-6.git19f2f28
- correct tag specification format in %%gobuild macro

* Fri Aug 24 2018 Lokesh Mandvekar <lsm5@redhat.com> - 0.7.3-5.git19f2f28
- Resolves: #1616062 - patch to revert coreos/go-iptables bump

* Wed Aug 08 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.3-4.git19f2f28
- Resolves:#1603012
- fix versioning, upstream got it wrong at 7.2

* Tue Aug 07 2018 Lokesh Mandvekar <lsm5@redhat.com> - 0.7.2-3.git19f2f28
- disable i686 temporarily for appstream builds
- update golang deps and gobuild definition

* Mon Aug 06 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.2-2.git19f2f28
- rebase

* Thu Jul 12 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.0-103.gitdd8ff8a
- enable scl with the toolset

* Tue Jul 03 2018 Lokesh Mandvekar <lsm5@redhat.com> - 0.7.0-102.gitdd8ff8a
- remove devel and unittest subpackages
- use new go-toolset deps
 
* Thu May 10 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.7.0-101
- rebase
- patches already upstream, removed

* Thu Apr 26 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.6.0-6
- Imported from Fedora
- Renamed CNI -> plugins

* Mon Apr  2 2018 Peter Robinson <pbrobinson@fedoraproject.org> 0.6.0-4
- Own the libexec cni directory

* Wed Feb 07 2018 Fedora Release Engineering <releng@fedoraproject.org> - 0.6.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Tue Jan 23 2018 Dan Williams <dcbw@redhat.com> - 0.6.0-2
- skip settling IPv4 addresses

* Mon Jan 08 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 0.6.0-1
- rebased to 7480240de9749f9a0a5c8614b17f1f03e0c06ab9

* Fri Oct 13 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0.5.2-7
- do not install to /opt (against Fedora Guidelines)

* Thu Aug 24 2017 Jan Chaloupka <jchaloup@redhat.com> - 0.5.2-6
- Enable devel subpackage

* Wed Aug 02 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.5.2-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Wed Jul 26 2017 Fedora Release Engineering <releng@fedoraproject.org> - 0.5.2-4
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Thu Jul 13 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0.5.2-3
- excludearch: ppc64 as it's not in goarches anymore
- re-enable s390x

* Fri Jun 30 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0.5.2-2
- upstream moved to github.com/containernetworking/plugins
- built commit dcf7368
- provides: containernetworking-plugins
- use vendored deps because they're a lot less of a PITA
- excludearch: s390x for now (rhbz#1466865)

* Mon Jun 12 2017 Timothy St. Clair <tstclair@heptio.com> - 0.5.2-1
- Update to 0.5.2 
- Softlink to default /opt/cni/bin directories

* Sun May 07 2017 Timothy St. Clair <tstclair@heptio.com> - 0.5.1-1
- Initial package

