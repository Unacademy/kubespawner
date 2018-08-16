from unittest.mock import Mock

from jupyterhub.objects import Hub, Server
import pytest
from traitlets.config import Config

from kubespawner import KubeSpawner


class MockUser(Mock):
    name = 'fake'
    server = Server()

    @property
    def url(self):
        return self.server.url


def test_deprecated_config():
    """Deprecated config is handled correctly"""
    cfg = Config()
    ks_cfg = cfg.KubeSpawner
    # both set, non-deprecated wins
    ks_cfg.singleuser_fs_gid = 5
    ks_cfg.fs_gid = 10
    # only deprecated set, should still work
    ks_cfg.singleuser_extra_pod_config = extra_pod_config = {"key": "value"}
    spawner = KubeSpawner(config=cfg, _mock=True)
    assert spawner.fs_gid == 10
    assert spawner.extra_pod_config == extra_pod_config
    # deprecated access gets the right values, too
    assert spawner.singleuser_fs_gid == spawner.fs_gid
    assert spawner.singleuser_extra_pod_config == spawner.singleuser_extra_pod_config


def test_deprecated_runtime_access():
    """Runtime access/modification of deprecated traits works"""
    spawner = KubeSpawner(_mock=True)
    spawner.singleuser_uid = 10
    assert spawner.uid == 10
    assert spawner.singleuser_uid == 10
    spawner.uid = 20
    assert spawner.uid == 20
    assert spawner.singleuser_uid == 20


@pytest.mark.asyncio
async def test_spawn(kube_ns, kube_client, config):
    spawner = KubeSpawner(hub=Hub(), user=MockUser(), config=config)
    # empty spawner isn't running
    status = await spawner.poll()
    assert isinstance(status, int)

    # start the spawner
    await spawner.start()
    # verify the pod exists
    pods = kube_client.list_namespaced_pod(kube_ns).items
    pod_names = [p.metadata.name for p in pods]
    assert "jupyter-%s" % spawner.user.name in pod_names
    # verify poll while running
    status = await spawner.poll()
    assert status is None
    # stop the pod
    await spawner.stop()

    # verify pod is gone
    pods = kube_client.list_namespaced_pod(kube_ns).items
    pod_names = [p.metadata.name for p in pods]
    assert "jupyter-%s" % spawner.user.name not in pod_names

    # verify exit status
    status = await spawner.poll()
    assert isinstance(status, int)

