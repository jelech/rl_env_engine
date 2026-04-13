"""
S3 数据传输: trajectory buffer 上传/下载。

Collector 将 trajectory 数据序列化后上传 S3，Learner 从 S3 拉取。
支持 snappy 压缩以减少传输量（约 2:1 压缩比）。
"""

import io
import logging
import pickle
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class S3Transport:
    """S3 trajectory 数据传输"""

    def __init__(
        self,
        bucket: str,
        prefix: str = "trajectories",
        region: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        use_compression: bool = True,
        max_workers: int = 8,
    ):
        self.bucket = bucket
        self.prefix = prefix
        self.use_compression = use_compression
        self.max_workers = max_workers

        try:
            import boto3
            kwargs = {}
            if region:
                kwargs["region_name"] = region
            if endpoint_url:
                kwargs["endpoint_url"] = endpoint_url
            self.s3 = boto3.client("s3", **kwargs)
            self._enabled = True
        except ImportError:
            logger.warning("boto3 not installed, S3 transport disabled")
            self.s3 = None
            self._enabled = False

    def _compress(self, data: bytes) -> bytes:
        if not self.use_compression:
            return data
        try:
            import snappy
            return snappy.compress(data)
        except ImportError:
            return data

    def _decompress(self, data: bytes) -> bytes:
        if not self.use_compression:
            return data
        try:
            import snappy
            return snappy.decompress(data)
        except ImportError:
            return data

    def upload_buffer(self, buffer_data: dict, version: int, collector_id: str) -> str:
        """
        上传一个 collector 的 buffer 数据到 S3。

        Returns:
            S3 key
        """
        if not self._enabled:
            raise RuntimeError("S3 transport not available (boto3 not installed)")

        raw = pickle.dumps(buffer_data)
        compressed = self._compress(raw)
        key = f"{self.prefix}/v{version}/{collector_id}.bin"

        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=compressed,
        )
        logger.info(f"Uploaded buffer to s3://{self.bucket}/{key} ({len(compressed)} bytes)")
        return key

    def download_buffer(self, version: int, collector_id: str) -> dict:
        """下载指定 collector 的 buffer 数据"""
        if not self._enabled:
            raise RuntimeError("S3 transport not available (boto3 not installed)")

        key = f"{self.prefix}/v{version}/{collector_id}.bin"
        resp = self.s3.get_object(Bucket=self.bucket, Key=key)
        compressed = resp["Body"].read()
        raw = self._decompress(compressed)
        return pickle.loads(raw)

    def download_all_buffers(self, version: int, collector_ids: List[str]) -> List[dict]:
        """并发下载所有 collector 的 buffer 数据"""
        if not self._enabled:
            raise RuntimeError("S3 transport not available (boto3 not installed)")

        results = [None] * len(collector_ids)

        def _download(idx, cid):
            results[idx] = self.download_buffer(version, cid)

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = [pool.submit(_download, i, cid) for i, cid in enumerate(collector_ids)]
            for f in futures:
                f.result()

        return results

    def list_versions(self) -> List[int]:
        """列出 S3 上已有的所有 version"""
        if not self._enabled:
            return []

        resp = self.s3.list_objects_v2(
            Bucket=self.bucket,
            Prefix=f"{self.prefix}/v",
            Delimiter="/",
        )
        versions = []
        for cp in resp.get("CommonPrefixes", []):
            prefix = cp["Prefix"]
            try:
                v = int(prefix.split("/v")[-1].rstrip("/"))
                versions.append(v)
            except (ValueError, IndexError):
                continue
        return sorted(versions)
