THIS_LIB = $(notdir $(abspath $(TOP_DIR)))
DEP_LIBS = duino_bus duino_log duino_util
ifneq ($(wildcard ../../libs/duino_littlfs),)
DEP_LIBS += duino_littlefs
endif
