"""
This file is part of nucypher.

nucypher is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

nucypher is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with nucypher.  If not, see <https://www.gnu.org/licenses/>.
"""

import time

from nucypher.characters.lawful import Ursula
from nucypher.config.characters import AliceConfiguration
from nucypher.utilities.logging import GlobalLoggerSettings
from nucypher.utilities.sandbox.middleware import MockRestMiddlewareForLargeFleetTests
from nucypher.utilities.sandbox.ursula import make_federated_ursulas
from tests.performance_mocks import mock_cert_storage, mock_cert_loading, mock_rest_app_creation, mock_cert_generation, \
    mock_secret_source, mock_remember_node, mock_record_fleet_state, mock_verify_node, mock_message_verification, \
    mock_metadata_validation, mock_signature_bytes, mock_stamp_call, mock_pubkey_from_bytes, VerificationTracker

"""
Node Discovery happens in phases.  The first step is for a network actor to learn about the mere existence of a Node.
This is a straightforward step which we currently do with our own logic, but which may someday be replaced by something
like libp2p, depending on the course of development of those sorts of tools.

After this, our "Learning Loop" does four other things in sequence which are not part of the offering of node discovery tooling alone:

* Instantiation of an actual Node object (currently, an Ursula object) from node metadata.
* Validation of the node's metadata (non-interactive; shows that the Node's public material is indeed signed by the wallet holder of its Staker).
* Verification of the Node itself (interactive; shows that the REST server operating at the Node's interface matches the node's metadata).
* Verification of the Stake (reads the blockchain; shows that the Node is sponsored by a Staker with sufficient Stake to support a Policy).

These tests show that each phase of this process is done correctly, and in some cases, with attention to specific
performance bottlenecks.
"""


def test_alice_can_learn_about_a_whole_bunch_of_ursulas(ursula_federated_test_config):

    with GlobalLoggerSettings.pause_all_logging_while():
        with mock_cert_storage, mock_cert_loading, mock_rest_app_creation, mock_cert_generation, mock_secret_source, mock_remember_node:
            _ursulas = make_federated_ursulas(ursula_config=ursula_federated_test_config,
                                              quantity=5000, know_each_other=False)
            all_ursulas = {u.checksum_address: u for u in _ursulas}
            for ursula in _ursulas:
                ursula.known_nodes._nodes = all_ursulas
                ursula.known_nodes.checksum = b"This is a fleet state checksum..".hex()
    config = AliceConfiguration(dev_mode=True,
                                network_middleware=MockRestMiddlewareForLargeFleetTests(),
                                known_nodes=_ursulas,
                                federated_only=True,
                                abort_on_learning_error=True,
                                save_metadata=False,
                                reload_metadata=False)

    with mock_cert_storage, mock_verify_node, mock_record_fleet_state:
        alice = config.produce(known_nodes=list(_ursulas)[:1])

    # We started with one known_node and verified it.
    # TODO: Consider changing this - #1449
    assert VerificationTracker.node_verifications == 1

    with mock_cert_storage, mock_cert_loading, mock_verify_node, mock_message_verification, mock_metadata_validation:
        with mock_pubkey_from_bytes, mock_stamp_call, mock_signature_bytes:
            started = time.time()
            alice.block_until_number_of_known_nodes_is(8, learn_on_this_thread=True, timeout=60)
            ended = time.time()
            elapsed = ended - started

    assert VerificationTracker.node_verifications == 1  # We have only verified the first Ursula.
    assert sum(isinstance(u, Ursula) for u in alice.known_nodes) < 20  # We haven't instantiated many Ursulas.
    assert elapsed < 8  # 8 seconds is still a little long to discover 8 out of 5000 nodes, but before starting the optimization that went with this test, this operation took about 18 minutes on jMyles' laptop.
