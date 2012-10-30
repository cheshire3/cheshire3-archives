"""Setuptools command sub-classes."""

import os
import shutil
import inspect

from os.path import abspath, dirname, join, exists, islink
from pkg_resources import normalize_path

from setuptools import Command
from setuptools.command import develop as _develop
from setuptools.command import install as _install

from cheshire3.internal import cheshire3Home, cheshire3Root

from apache import ApacheModifier
from exceptions import *


class unavailable_command(Command):
    """Sub-class commands that we don't want to make available."""

    description = "Command is not appropriate for this package"
    user_options = []
    boolean_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        raise NotImplementedError(self.description)


class c3_command(Command):
    """Base Class for custom commands."""
    
    user_options = [
        ("with-httpd=",
         None,
         "Set the path to Apache HTTPD installation directory"),
    ]

    def initialize_options(self):
        self.with_httpd = join(cheshire3Home, 'install')
        self.db_plugin_path = os.path.join(cheshire3Root,
                                           'configs',
                                           'databases',
                                           'db_ead.xml')

    def finalize_options(self):
        self.with_httpd = normalize_path(self.with_httpd)

    def install_apache_mods(self):
        """Install Apache HTTPD modifications."""
        # Install Apache HTTPD configuration plugin file
        am = ApacheModifier(self.with_httpd)
        am.install_apache_config()
        # Create web directory for static search pages
        # and install default landing page there
        am.install_web_landing_page()
        
    def uninstall_apache_mods(self):
        # Install Apache HTTPD configuration plugin file
        am = ApacheModifier(self.with_httpd)
        am.uninstall_apache_config()
        # Remove web directory for static search pages
        am.uninstall_web_dir()
    

class develop(_develop.develop, c3_command):
    
    user_options = _develop.develop.user_options + c3_command.user_options
    
    def initialize_options(self):
        _develop.develop.initialize_options(self)
        c3_command.initialize_options(self)

    def finalize_options(self):
        _develop.develop.finalize_options(self)
        c3_command.finalize_options(self)
        
    def install_for_development(self):
        global distropath
        # Carry out normal procedure
        _develop.develop.install_for_development(self)
        # Check for existing install / development install
        # by checking for Cheshire3 config plugin file
        c3_plugin_path = join('cheshire3',
                            'dbs',
                            'configs.d',
                            'db_ead.xml')
        if exists(self.db_plugin_path):
            if islink(self.db_plugin_path):
                raise DevelopException("Already installed in 'develop' mode")
            else:
                raise DevelopException("""\
Package is already installed. To install in 'develop' mode you must first \
run the 'uninstall' command.""")
        # Install Apache HTTPD mods
        self.install_apache_mods()
        # Create symbolic links
        # Link to Cheshire3 database config plugin
        os.symlink(join(distropath, c3_plugin_path), 
                   self.db_plugin_path)
        # Link to database directory
        subpath = join('cheshire3', 
                       'dbs', 
                       'ead')
        os.symlink(join(distropath, 'dbs', 'ead'), 
                   join(cheshire3Home, subpath))
        # Link to web app directory
        subpath = join('cheshire3', 
                       'www', 
                       'ead')
        os.symlink(join(distropath, 'www'), 
                   join(cheshire3Home, subpath))
        
    def uninstall_link(self):
        # Carry out normal procedure
        _develop.develop.uninstall_link(self)
        # Uninstall Apache HTTPD mods
        self.uninstall_apache_mods()
        # Remove symbolic links
        # Link to Cheshire3 database config plugin
        os.remove(self.db_plugin_path)
        # Link to database directory
        os.remove(join(cheshire3Home, 
                       'cheshire3', 
                       'dbs', 
                       'ead'))
        # Link to web app directory
        os.remove(join(cheshire3Home, 
                       'cheshire3', 
                       'www', 
                       'ead'))


class install(_install.install, c3_command):
    
    user_options = _install.install.user_options + c3_command.user_options
    
    def initialize_options(self):
        _install.install.initialize_options(self)
        c3_command.initialize_options(self)

    def finalize_options(self):
        _install.install.finalize_options(self)
        c3_command.finalize_options(self)
        
    def run(self):
        # Carry out normal procedure
        _install.install.run(self)
        # Check for existing install / development install
        # by checking for Cheshire3 config plugin file
        c3_plugin_path = join('cheshire3',
                       'dbs', 
                       'configs.d', 
                       'db_ead.xml')
        if exists(self.db_plugin_path):
            if islink(self.db_plugin_path):
                raise InstallException("""\
Package is already installed in 'develop' mode. To install it you must first \
run the `develop` command again with the `--uninstall` option.""")
            else:
                raise InstallException("Already installed.")
        # Install Apache HTTPD mods
        self.install_apache_mods()
        # Install Cheshire3 database config plugin
        shutil.copy(join(distropath, c3_plugin_path), self.db_plugin_path)
        # Install database directory
        subpath = join('cheshire3', 
                       'dbs', 
                       'ead')
        shutil.copytree(join(distropath, 'dbs', 'ead'), 
                        join(cheshire3Home, subpath),
                        symlinks=False,
                        ignore=shutil.ignore_patterns(".git*", 
                                                      "*.pyc",
                                                      "PyZ3950_parsetab.py*", 
                                                      "*.bdb", 
                                                      "*.log")
                        )
        # Install to web app directory
        # Install database directory
        subpath = join('cheshire3', 
                       'www', 
                       'ead')
        shutil.copytree(join(distropath, 'www'), 
                        join(cheshire3Home, subpath),
                        symlinks=False,
                        ignore=shutil.ignore_patterns(".git*", 
                                                      "*.pyc", 
                                                      "PyZ3950_parsetab.py*", 
                                                      "*.bdb", 
                                                      "*.log")
                        )


class uninstall(c3_command):

    description = "Uninstall Cheshire3 for Archives"
    
    def run(self):
        # Check for existing install / development install
        # by checking for Cheshire3 config plugin file
        c3_plugin_path = join('cheshire3',
                       'dbs', 
                       'configs.d', 
                       'db_ead.xml')
        if not exists(self.db_plugin_path):
            raise UninstallException("Package is not installed.")
        elif islink(self.db_plugin_path):
            raise UninstallException("""\
Package was installed in 'develop' mode. To uninstall, you should run the \
`develop` command with the `--uninstall` option.""")
        # Uninstall Apache HTTPD mods
        self.uninstall_apache_mods()
        # Uninstall Cheshire3 database config plugin
        os.remove(self.db_plugin_path)
        # Uninstall database directory
        subpath = join('cheshire3', 
                       'dbs', 
                       'ead')
        shutil.rmtree(join(cheshire3Home, subpath))
        # Uninstall to web app directory
        subpath = join('cheshire3', 
                       'www', 
                       'ead')
        shutil.rmtree(join(cheshire3Home, subpath))


# Inspect to find current path
modpath = inspect.getfile(inspect.currentframe())
distropath = abspath(join(dirname(modpath), '..'))


