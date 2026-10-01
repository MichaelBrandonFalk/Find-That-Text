(function () {
  const root = document.documentElement;
  const repo = root.dataset.repo || "find-that-text";
  const fallbackOwner = root.dataset.owner || "OWNER";
  const inferredOwner = location.hostname.endsWith(".github.io")
    ? location.hostname.split(".")[0]
    : fallbackOwner;
  const owner = inferredOwner === "OWNER" ? fallbackOwner : inferredOwner;
  const repoUrl = `https://github.com/${owner}/${repo}`;
  const latestUrl = `${repoUrl}/releases/latest`;

  for (const [id, url] of [
    ["source", repoUrl],
    ["readme", `${repoUrl}#readme`],
    ["readme-inline", `${repoUrl}#readme`],
    ["releases", `${repoUrl}/releases`],
    ["license", `${repoUrl}/blob/main/LICENSE`],
  ]) {
    const element = document.getElementById(id);
    if (element) element.href = url;
  }

  const download = document.getElementById("download");
  const windowsDownload = document.getElementById("download-windows");
  const linuxDownload = document.getElementById("download-linux");
  const status = document.getElementById("download-status");
  if (!download || !windowsDownload || !linuxDownload || !status || owner === "OWNER") {
    if (download) download.href = latestUrl;
    if (windowsDownload) windowsDownload.href = latestUrl;
    if (linuxDownload) linuxDownload.href = latestUrl;
    return;
  }

  fetch(`https://api.github.com/repos/${owner}/${repo}/releases/latest`, {
    headers: { Accept: "application/vnd.github+json" },
  })
    .then((response) => {
      if (!response.ok) throw new Error("No release metadata");
      return response.json();
    })
    .then((release) => {
      const macAsset = (release.assets || []).find((item) =>
        /macOS-Apple-Silicon\.dmg$/i.test(item.name)
      );
      const windowsAsset = (release.assets || []).find((item) =>
        /Windows-x64\.zip$/i.test(item.name)
      );
      const linuxAsset = (release.assets || []).find((item) =>
        /Linux-x64\.tar\.gz$/i.test(item.name)
      );
      download.href = macAsset ? macAsset.browser_download_url : release.html_url || latestUrl;
      windowsDownload.href = windowsAsset ? windowsAsset.browser_download_url : release.html_url || latestUrl;
      linuxDownload.href = linuxAsset ? linuxAsset.browser_download_url : release.html_url || latestUrl;
      status.textContent = macAsset && windowsAsset && linuxAsset
        ? `Current version: ${release.tag_name}`
        : "Open the latest GitHub Release to choose a build.";
    })
    .catch(() => {
      download.href = latestUrl;
      windowsDownload.href = latestUrl;
      linuxDownload.href = latestUrl;
      status.textContent = "Release metadata is unavailable. The button opens the latest GitHub Release.";
    });
})();
