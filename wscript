#! /usr/bin/env python
# encoding: utf-8

import os
from Configure import g_maxlen
import Params
import time
import Task
import re

APPNAME='a2jmidid'
VERSION='7'

# these variables are mandatory ('/' are converted automatically)
srcdir = '.'
blddir = 'build'

def create_gitversion_gen(bld, header='gitversion.h', define=None):
    cmd = '../gitversion_regenerate.sh ${TGT}'
    if define:
        cmd += " " + define
    cls = Task.simple_task_type('gitversion', cmd, color='BLUE')
    cls.must_run = lambda self: True
    #cls.before = 'cxx'

    def sg(self):
        rt = Params.h_file(self.m_outputs[0].abspath(self.env()))
        return rt
    cls.signature = sg

    #def se(self):
    #    r = sg(self)
    #    return (r, r, r, r, r)
    #cls.cache_sig = property(sg, None)
    cls.cache_sig = None

    tsk = cls('gitversion', bld.env().copy())
    tsk.m_inputs = []
    tsk.m_outputs = [bld.path.find_or_declare(header)]
    tsk.prio = 1 # execute this task first

def display_msg(msg, status = None, color = None):
    sr = msg
    global g_maxlen
    g_maxlen = max(g_maxlen, len(msg))
    if status:
        print "%s :" % msg.ljust(g_maxlen),
        Params.pprint(color, status)
    else:
        print "%s" % msg.ljust(g_maxlen)

def set_options(opt):
    opt.tool_options('compiler_cc')
    opt.add_option('--enable-pkg-config-dbus-service-dir', action='store_true', default=False, help='force D-Bus service install dir to be one returned by pkg-config')
    opt.add_option('--disable-dbus', action='store_true', default=False, help="Don't enable D-Bus support even if required dependencies are present")
    opt.add_option('--mandir', type='string', help="Manpage directory [Default: <prefix>/share/man]")

def configure(conf):
    conf.check_tool('compiler_cc')

    conf.check_pkg('alsa', mandatory=True)
    conf.check_pkg('jack', vnum="0.109.0", mandatory=True)
    if not Params.g_options.disable_dbus:
        conf.check_pkg('dbus-1', mandatory=False, pkgvars=['session_bus_services_dir'])
        conf.env['DBUS_ENABLED'] = 'LIB_DBUS-1' in conf.env
    else:
        conf.env['DBUS_ENABLED'] = False

    conf.env['LIB_DL'] = ['dl']

    #conf.check_header('expat.h', mandatory=True)
    #conf.env['LIB_EXPAT'] = ['expat']
    conf.check_header('getopt.h', mandatory=True)

    if conf.env['DBUS_ENABLED']:
        if Params.g_options.enable_pkg_config_dbus_service_dir:
            conf.env['DBUS_SERVICES_DIR'] = conf.env['DBUS-1_SESSION_BUS_SERVICES_DIR'][0]
        else:
            conf.env['DBUS_SERVICES_DIR'] = os.path.normpath(conf.env['PREFIX'] + '/share/dbus-1/services')

        conf.check_tool('misc')             # dbus service file subst tool

    if Params.g_options.mandir:
        conf.env['MANDIR'] = Params.g_options.mandir
    else:
        conf.env['MANDIR'] = conf.env['PREFIX'] + '/share/man'

    conf.define('A2J_VERSION', VERSION)
    conf.write_config_header('config.h')

    gitrev = None
    if os.access('gitversion.h', os.R_OK):
        data = file('gitversion.h').read()
        m = re.match(r'^#define GIT_VERSION "([^"]*)"$', data)
        if m != None:
            gitrev = m.group(1)

    print
    display_msg("==================")
    version_msg = "a2jmidid-" + VERSION
    if gitrev:
        version_msg += " exported from " + gitrev
    else:
        version_msg += " git revision will checked and eventually updated during build"
    print version_msg
    print

    display_msg("Install prefix", conf.env['PREFIX'], 'CYAN')
    if conf.env['DBUS_ENABLED']:
        have_dbus_status = "yes"
    else:
        have_dbus_status = "no"
    display_msg("D-Bus support", have_dbus_status)
    if conf.env['DBUS_ENABLED']:
        display_msg('D-Bus service install directory', conf.env['DBUS_SERVICES_DIR'], 'CYAN')
        if conf.env['DBUS_SERVICES_DIR'] != conf.env['DBUS-1_SESSION_BUS_SERVICES_DIR'][0]:
            print
            print Params.g_colors['RED'] + "WARNING: D-Bus session services directory as reported by pkg-config is"
            print Params.g_colors['RED'] + "WARNING:",
            print Params.g_colors['CYAN'] + conf.env['DBUS-1_SESSION_BUS_SERVICES_DIR'][0]
            print Params.g_colors['RED'] + 'WARNING: but service file will be installed in'
            print Params.g_colors['RED'] + "WARNING:",
            print Params.g_colors['CYAN'] + conf.env['DBUS_SERVICES_DIR']
            print Params.g_colors['RED'] + 'WARNING: You may need to adjust your D-Bus configuration after installing'
            print 'WARNING: You can override dbus service install directory'
            print 'WARNING: with --enable-pkg-config-dbus-service-dir option to this script'
            print Params.g_colors['NORMAL'],
    print

def build(bld):
    if not os.access('gitversion.h', os.R_OK):
        create_gitversion_gen(bld)

    prog = bld.create_obj('cc', 'program')
    prog.source = [
        'a2jmidid.c',
        'log.c',
        'port.c',
        'port_thread.c',
        'port_hash.c',
        'paths.c',
        #'conf.c',
        'jack.c',
        'list.c',
        ]

    if bld.env()['DBUS_ENABLED']:
        prog.source.append('dbus.c')
        prog.source.append('dbus_iface_introspectable.c')
        prog.source.append('dbus_iface_control.c')
        prog.source.append('sigsegv.c')

    prog.includes = '.' # make waf dependency tracking work
    prog.target = 'a2jmidid'
    prog.uselib = 'ALSA JACK DL'
    if bld.env()['DBUS_ENABLED']:
        prog.uselib += " DBUS-1"
    prog = bld.create_obj('cc', 'program')
    prog.source = 'a2jmidi_bridge.c'
    prog.target = 'a2jmidi_bridge'
    prog.uselib = 'ALSA JACK'

    prog = bld.create_obj('cc', 'program')
    prog.source = 'j2amidi_bridge.c'
    prog.target = 'j2amidi_bridge'
    prog.uselib = 'ALSA JACK'

    if bld.env()['DBUS_ENABLED']:
        # process org.gna.home.a2jmidid.service.in -> org.gna.home.a2jmidid.service
        obj = bld.create_obj('subst')
        obj.source = 'org.gna.home.a2jmidid.service.in'
        obj.target = 'org.gna.home.a2jmidid.service'
        obj.dict = {'BINDIR': bld.env()['PREFIX'] + '/bin'}
        obj.inst_var = bld.env()['DBUS_SERVICES_DIR']
        obj.inst_dir = '/'

        install_files('PREFIX', 'bin', 'a2j_control', chmod=0755)
        install_files('PREFIX', 'bin', 'a2j', chmod=0755)

    # install man pages
    man_pages = [
        "a2jmidi_bridge.1",
        "a2jmidid.1",
        "j2amidi_bridge.1",
        ]

    if bld.env()['DBUS_ENABLED']:
        man_pages.append("a2j.1")
        man_pages.append("a2j_control.1")

    for i in range(len(man_pages)):
        man_pages[i] = "man/" + man_pages[i]

    install_files('MANDIR', 'man1', man_pages)

def dist_hook():
    os.remove('gitversion_regenerate.sh')
    os.system('../gitversion_regenerate.sh gitversion.h')
