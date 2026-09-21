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
  const status = document.getElementById("download-status");
  if (!download || !status || owner === "OWNER") {
    if (download) download.href = latestUrl;
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
      const asset = (release.assets || []).find((item) =>
        /macOS-Apple-Silicon\.dmg$/i.test(item.name)
      );
      download.href = asset ? asset.browser_download_url : release.html_url || latestUrl;
      status.textContent = asset
        ? `Current version: ${release.tag_name}`
        : "Open the latest GitHub Release to download the Mac build.";
    })
    .catch(() => {
      download.href = latestUrl;
      status.textContent = "Release metadata is unavailable. The button opens the latest GitHub Release.";
    });
})();
