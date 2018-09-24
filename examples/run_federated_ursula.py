# This is not an actual mining script.  Don't use this to mine - you won't
# perform any re-encryptions, and you won't get paid.
# It might be (but might not be) useful for determining whether you have
# the proper depedencies and configuration to run an actual mining node.

# WIP w/ hendrix@tags/3.3.0rc1

import asyncio
import binascii
import logging
import os
import shutil
import sys

from nucypher.characters.lawful import Ursula

root = logging.getLogger()
root.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

MY_REST_PORT = sys.argv[1]
# TODO: Use real path tooling here.
SHARED_CRUFTSPACE = "{}/examples-runtime-cruft".format(os.path.dirname(os.path.abspath(__file__)))
CRUFTSPACE = "{}/{}".format(SHARED_CRUFTSPACE, MY_REST_PORT)
DB_NAME = "{}/database".format(CRUFTSPACE)
CERTIFICATE_DIR = "{}/certs".format(CRUFTSPACE)


def spin_up_ursula(rest_port, db_name, teachers=(), certificate_dir=None):
    metadata_file = "examples-runtime-cruft/node-metadata-{}".format(rest_port)

    asyncio.set_event_loop(asyncio.new_event_loop())  # Ugh.  Awful.  But needed until we shed the DHT.
    _URSULA = Ursula(rest_port=rest_port,
                     rest_host="localhost",
                     db_name=db_name,
                     federated_only=True,
                     known_nodes=teachers,
                     known_certificates_dir=certificate_dir
                     )
    try:
        with open(metadata_file, "w") as f:
            f.write(bytes(_URSULA).hex())
        _URSULA.start_learning_loop()
        _URSULA.get_deployer().run()
    finally:
        os.remove(db_name)
        os.remove(metadata_file)


if __name__ == "__main__":
    try:
        shutil.rmtree(CRUFTSPACE, ignore_errors=True)
        os.mkdir(CRUFTSPACE)
        os.mkdir(CERTIFICATE_DIR)
        try:
            teacher_rest_port = sys.argv[2]
            # TODO: Implement real path tooling here.
            with open("{}/node-metadata-{}".format(SHARED_CRUFTSPACE,
                                                   teacher_rest_port), "r") as f:
                f.seek(0)
                teacher_bytes = binascii.unhexlify(f.read())
            teacher = Ursula.from_bytes(teacher_bytes,
                                        federated_only=True)
            teacher.save_certificate_to_disk(directory=CERTIFICATE_DIR)
            teachers = (teacher,)
            print("Will learn from {}".format(teacher))
        except IndexError:
            teachers = ()
        except FileNotFoundError as e:
            raise ValueError("Can't find a metadata file for node {}".format(teacher_rest_port))

        spin_up_ursula(MY_REST_PORT, DB_NAME,
                       teachers=teachers,
                       certificate_dir=CERTIFICATE_DIR)
    finally:
        shutil.rmtree(CRUFTSPACE)
