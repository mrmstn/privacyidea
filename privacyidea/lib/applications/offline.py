# -*- coding: utf-8 -*-
#
#  privacyIDEA
#  2015-03-13 Cornelius Kölbel, <cornelius@privacyidea.org>
#             initial writeup
#
# License:  AGPLv3
#  contact:  http://www.privacyidea.org
#
# This code is free software; you can redistribute it and/or
# modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
# License as published by the Free Software Foundation; either
# version 3 of the License, or any later version.
#
# This code is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU AFFERO GENERAL PUBLIC LICENSE for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from privacyidea.lib.applications import MachineApplicationBase
import logging
from privacyidea.lib.crypto import salted_hash_256
from privacyidea.lib.token import get_tokens
log = logging.getLogger(__name__)

class MachineApplication(MachineApplicationBase):
    """
    This is the application for Offline authentication with PAM or
    the privacyIDEA credential provider.

    The machine application returns a list of salted OTP hashes to be used with
    offline authentication. The token then is disabled, so that it can not
    be used for online authentication anymore, to avoid reusing a fished OTP
    value.

    The server stores the information, which OTP values were issued.

    options options:
      * user: a username.
      * count: is the number of OTP values returned

    """
    application_name = "offline"

    @classmethod
    def get_authentication_item(cls,
                                token_type,
                                serial,
                                challenge=None, options=None):
        """
        :param token_type: the type of the token. At the moment
                           we only support "HOTP" token. Supporting time
                           based tokens is difficult, since we would have to
                           return a looooong list of OTP values.
                           Supporting "yubikey" token (AES) would be
                           possible, too.
        :param serial:     the serial number of the token.
        :param challenge:  n/a
        :type challenge:   hex string
        :return auth_item: A list of hashed OTP values
        """
        ret = {}
        options = options or {}
        if token_type.lower() == "hotp":
            count = int(options.get("count", 100))
            # get the token
            toks = get_tokens(serial=serial)
            if len(toks) == 1:
                token_obj = toks[0]
                (res, err, otp_dict) = token_obj.get_multi_otp(count=count)
                otps = otp_dict.get("otp")
                for key in otps.keys():
                    # TODO: We could not only hash the OTP value but also the
                    #  salted_hash_256(OTP PIN + OTP value)
                    otps[key] = salted_hash_256(otps.get(key))
                # Disable the token, that is used for offline authentication
                token_obj.enable(False)
                # increase the counter by the consumed values and
                # also store it in tokeninfo.
                token_obj.inc_otp_counter(counter=count)
                token_obj.add_tokeninfo(key="offline_counter",
                                        value=count)
                ret["response"] = otps
                user_object = token_obj.get_user()
                if user_object:
                    uInfo = user_object.get_user_info()
                    if "username" in uInfo:
                        ret["username"] = uInfo.get("username")

        else:
            log.info("Token %r, type %r is not supported by"
                     "OFFLINE application module" % (serial, token_type))

        return ret

    @classmethod
    def get_options(cls):
        """
        returns a dictionary with a list of required and optional options
        """
        return {'required': [],
                'optional': ['user', 'count']}
