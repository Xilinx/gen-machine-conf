#!/usr/bin/env python3

# Copyright (C) 2022-2026, Advanced Micro Devices, Inc.  All rights reserved.
#
# Author:
#       Raju Kumar Pothuraju <rajukumar.pothuraju@amd.com>
#
# SPDX-License-Identifier: MIT

import os
import logging
import time
import common_utils

logger = logging.getLogger('Gen-Machineconf')

# Common bitbake variable
Bitbake = None


class FetchError(Exception):
    """Fetch exception transferred from bitbake"""
    def __init__(self, message, url = None):
        if url:
            msg = "Fetcher failure for URL: '%s'. %s" % (url, message)
        else:
            msg = "Fetcher failure: %s" % message
        Exception.__init__(self, msg)
        self.args = (message, url)


class bitbake():
    disabled = False
    disabled_exception = None
    tinfoil = None
    tinfoilPrepared = False
    recipes_parsed = False
    prepare_args = None

    def __init__(self, config_only=False, prefile=[], disabled=False):
        if disabled:
            self.disabled = True
            self.disabled_reason = "Not initialized"
        else:
            try:
                import bb.tinfoil
            except Exception as e:
                self.disabled = True
                self.disabled_reason = "Import of bb.tinfoil failed: " + str(e)

        self.prepare_args = { 'config_only':config_only , 'prefile':prefile }

    def __del__(self):
        self.shutdown()

    # Typlical flow:
    #  initialize
    #  prepare
    #  parse_recipes (optional)
    #  getVar/setVar
    #
    # Bitbake commands:
    #  initialize
    #  prepare
    #  runBitbakeCmd
    #
    # Component Download:
    #  initialize
    #  prepare


    def initialize(self):
        if self.disabled:
            raise Exception("Bitbake is not available: " + self.disabled_reason)

        self.tinfoil = bb.tinfoil.Tinfoil(tracking=False)
        self.tinfoilPrepared = False

    def shutdown(self):
        logger.debug('Shutting down bitbake')

        if self.tinfoil:
            # No recovery if we can't shutdown, just accept any exceptions
            try:
                self.tinfoil.shutdown()
            except:
                pass
            time.sleep(3)

        self.tinfoil = None
        self.tinfoilPrepared = False
        self.recipes_parsed = False
        # Do NOT reset prepare_args!

    def prepare(self, config_only=False, prefile=[]):
        logger.debug('Prepare bitbake')

        self.prepare_args = { 'config_only':config_only , 'prefile':prefile }

        if self.disabled:
            return

        if self.tinfoilPrepared == True:
            logger.info('Configuration change, restarting bitbake')
            self.shutdown()

        if not self.tinfoil:
            self.initialize()

        try:
            self.tinfoilConfig = bb.tinfoil.TinfoilConfigParameters(config_only=config_only, quiet=2, prefile=prefile)
            self.tinfoil.prepare(config_only=config_only, quiet=2, config_params=self.tinfoilConfig)
            self.tinfoilPrepared = True
            self.recipes_parsed = False
        except bb.BBHandledException as e:
            raise Exception("Bitbake failed to start")

    def prepare_again(self):
        logger.debug('Prepare bitbake again (configuration change)')

        if self.disabled:
            return

        if self.prepare_args:
            self.prepare(config_only=self.prepare_args['config_only'], prefile=self.prepare_args['prefile'])
        else:
            self.prepare()

    def parse_recipes(self):
        logger.debug('Bitbake parsing recipes')

        if self.disabled:
            return

        if not self.tinfoilPrepared:
            self.prepare_again()
        if not self.recipes_parsed:
            # Emulate self.parse_recipes, but with our config
            #self.tinfoil.parse_recipes()
            # run_actions requires config_only set to False
            self.prepare_args['config_only'] = False
            self.tinfoilConfig = bb.tinfoil.TinfoilConfigParameters(config_only=self.prepare_args['config_only'], quiet=2, prefile=self.prepare_args['prefile'])
            try:
                self.tinfoil.run_actions(config_params=self.tinfoilConfig)
            except bb.tinfoil.TinfoilUIException as e:
                # Something went very wrong, shutdown bitbake and disable it
                self.shutdown()
                self.disabled = True
                raise Exception("Bitbake failed tinfoil.run_actions: %s" % e)
            self.tinfoil.recipes_parsed = True
            self.recipes_parsed = True

    def expand(self, variable, recipe=None):
       '''Return back the expanded values of bitbake variables with an optional recipe'''
       if self.disabled:
           return variable

       logger.debug('Expanding bitbake variable %s from %s' % (variable, recipe))

       d = None
       try:
           if recipe:
               if not self.recipes_parsed:
                   self.parse_recipes()
               d = self.tinfoil.parse_recipe(recipe)
           else:
               if not self.tinfoilPrepared:
                   self.prepare()
               d = self.tinfoil.config_data
       except:
           # Something went wrong in bitbake, we accept that and return 'variable'
           return variable
       return d.expand(variable)

    def getVar(self, variable, recipe=None):
      '''Return back the values of bitbake variables with an optional recipe'''
      if self.disabled:
          return None

      logger.debug('Getting bitbake variable %s from %s' % (variable, recipe))

      d = None
      try:
          if recipe:
              if not self.recipes_parsed:
                  self.parse_recipes()
              d = self.tinfoil.parse_recipe(recipe)
          else:
              if not self.tinfoilPrepared:
                  self.prepare()
              d = self.tinfoil.config_data
      except:
          # Something went wrong in bitbake, we accept that and return 'nothing'
          return None

      return d.getVar(variable)

    def setVar(self, variable, value):
        '''Set a bitbake variable. Note: this can NOT be used to set something that effects recipe parsing!'''
        logger.debug('Set bitbake variable %s to %s' % (variable, value))

        if self.disabled:
            return

        if not self.tinfoilPrepared:
            self.prepare()
        d = self.tinfoil.config_data

        d.setVar(variable, value)

    def runBitbakeCmd(self, recipe, task=None):
        '''Run a bitbake command.  Note there is a bug that the prefile isn't evaluated prior to parsing if parse_recipes has been run.'''
        '''This may require us to shutdown bitbake, and reconfigure WITHOUT recipe_parsed!'''
        logger.debug('Running bitbake recipe %s (task %s)' % (recipe, task))

        if self.disabled:
            raise Exception("Bitbake is unavailable to build task %s from recipe %s" % (task, recipe))

        return self.tinfoil.build_targets(recipe, task)

    def fetchAndUnpackURI(self, uri):
        ''' Use bb.fetch2.Fetch to download the specified URL's
        and unpack to TOPDIR/hw-description if bitbake found.'''
        if self.disabled:
            return Exception("Bitbake is unavailable to run fetch and download.")

        if os.path.exists(uri):
            # Add file:// prefix if its local file
            uri = 'file://%s' % os.path.abspath(uri)

        if not self.tinfoilPrepared:
            self.prepare_again()

        d = self.tinfoil.config_data
        localdata = d.createCopy()

        # BB_STRICT_CHECKSUM - To skip the checksum for network files
        localdata.setVar('BB_STRICT_CHECKSUM', 'ignore')
        # PREMIRRORS,MIRRORS - Skip fetching from MIRRORS
        #localdata.setVar('PREMIRRORS', '')
        #localdata.setVar('MIRRORS', '')
        try:
            fetcher = bb.fetch2.Fetch([uri], localdata)
            fetcher.download()

            # Unpack to hw-description
            hw_dir = os.path.join(localdata.getVar('TOPDIR'), '.hw-description')
            common_utils.RemoveDir(hw_dir)
            common_utils.CreateDir(hw_dir)
            fetcher.unpack(hw_dir)
        except bb.fetch2.FetchError as e:
            raise FetchError(message=e, url=uri)
        hw_dir_root = hw_dir
        # Get the S from url if exists, Helps if the specified path or url has multiple
        # SDT/XSA directories user can specify sub source directory. similar to
        # S variable in bb files.
        s_dir = ''
        localpath = ''
        for url in fetcher.urls:
            s_dir = fetcher.ud[url].parm.get('S') or ''
            localpath = fetcher.ud[url].localpath
            if url.startswith("file:///"):
                # If the file can't be unpacked or refers to a directory
                # then it will be in the same directory structure as the
                # original file:// URL.  hw_dir = ${WORKDIR}
                base_sdir = os.path.dirname(uri[8:])
                maybe_s_dir = os.path.join(base_sdir, s_dir)
                if os.path.exists(os.path.join(hw_dir, maybe_s_dir)):
                    s_dir = maybe_s_dir
            elif url.startswith("git://"):
                s_dir = os.path.join('git', s_dir)

        if s_dir:
            hw_dir = os.path.join(hw_dir, s_dir)

        return hw_dir, hw_dir_root, uri, s_dir, localpath


def InitializeBitbake(parserhelp):
    '''Initialize bitbake server and prepare it for use'''
    import sys
    # PetaLinux configuration tool skips bitbake usage
    if 'PETALINUX' in os.environ.keys() or '--petalinux' in sys.argv:
        startBitbake(disabled=True)
    else:
        # Try to start bitbake
        try:
            startBitbake()
        except Exception as e:
            if not parserhelp:
                if '--native-sysroot' in sys.argv:
                    logger.debug(str(e))
                    logger.warning("Unable to start the bitbake server, bitbake may be required to build any missing tools and configurations.")
                else:
                    logger.error(str(e))
                    raise Exception("Unable to start the bitbake server, bitbake is required for various tools and configurations.  " \
                                    "Be sure to have bitbake in your environment's PATH and PYTHONPATH.  See oe-init-build-env.")
        if not Bitbake.disabled:
            try:
                # prepare can fail if there is an invalid configuration
                Bitbake.prepare(True)
            except Exception as e:
                Bitbake.shutdown()
                Bitbake.disabled = True
                logger.error("The error above must be corrected before running gen-machine-conf.\n")
                if not parserhelp:
                    raise e


def startBitbake(disabled=False):
    global Bitbake
    if not Bitbake:
        Bitbake = bitbake(disabled=disabled)
        if not disabled:
            try:
                Bitbake.initialize()
            except Exception as e:
                Bitbake.shutdown()
                Bitbake.disabled = True
                raise e


def FindNativeSysroot(recipe):
    '''Based on oe-find-native-sysroot, purpose is to find a recipes sysroot'''
    if not recipe:
        return ""

    # That has already been done, don't repeat!
    if recipe in FindNativeSysroot.recipe_list:
        return

    recipe_staging_dir = None
    try:
        recipe_staging_dir = Bitbake.getVar('STAGING_DIR_NATIVE', recipe)
    except TypeError:
        recipe_staging_dir = None
    except KeyError:
        recipe_staging_dir = None
    except Exception as e:
        raise Exception("Unable to get required %s sysroot path.\nError: %s" % (recipe, e))

    if not recipe_staging_dir:
        raise Exception("Unable to get required %s sysroot path" % recipe)

    if recipe and not os.path.exists(recipe_staging_dir):
        # Make sure the sysroot is available to us
        logger.info('Constructing %s recipe sysroot...' % recipe)

        Bitbake.runBitbakeCmd(recipe, "addto_recipe_sysroot")

        if not recipe_staging_dir:
            raise Exception("Unable to get %s sysroot path after building" % recipe)

    common_utils.AddNativeSysrootPath(recipe_staging_dir)

    FindNativeSysroot.recipe_list.append(recipe)

# Default
FindNativeSysroot.recipe_list = []
