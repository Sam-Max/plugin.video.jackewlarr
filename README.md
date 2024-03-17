
# Jacktook

A Kodi addon for torrent finding and streaming. 

## Requirements.

- Kodi 19+

## Features.

Torrent Search:
- Jackett 
- Prowlarr 
- Torrentio 
- Elhosted 

Torrent Engines:
- Torrest
- Elementum
- Real Debrid 
- Premiumize 

Metadata:
- TMDB  
- AniList, Simkl (Anime)
- Fanart.tv
- TMDB helper

Others:
- API calls caching


## Installation of this addon (Jacktook)

The recommended way of installing the addon is through its [repository](https://github.com/Sam-Max/repository.jacktook), so that any updates will be automatically installed.

You can also install the addon without installing its repository. To do so, get the [latest release](https://github.com/Sam-Max/plugin.video.jacktook/releases/download/v0.1.4/plugin.video.jacktook-0.2.1.zip) from github. Please note that, if there are any additional dependencies, they won't be resolved unless the repository is installed.

## Steps.

1. Install this addon (recommended way of installing the addon is through its repository)

2. Add configuration on addon settings to connect with Jackett, Prowlarr or Torrentio. 

3. Install either [Torrest](https://github.com/i96751414/plugin.video.torrest) or [Elementum](https://elementumorg.github.io/) addons.


**Notes**:
1. Jackett and Prowlarr are optional if using Torrentio/Elfhosted.
1. Torrest/Elementum is optional if using Debrid service.
2. Prowlarr IndexerIds field is comma separated trackers ids without space. Ex. 12,13,14. (from version 0.1.5)
3. When using Jackett or Prowlarr: select only a few trackers (3-4 max), avoid trackers with cloudflare protection (unless you configure FlareSolverr), and select if available on trackers options to retrieve magnets as priority and not torrent files, to improve search speed and results.
4. You can deploy/install on a remote server (instructions more below) the [Torrest Service](https://github.com/i96751414/torrest-cpp) (torrent client that comes built-in on Torrest Addon that provides an API specially made for streaming). After that, you need to configure Torrest Addon with the Torrest Service IP/Domain and Port.

## How to run Jackett service using Docker:

Detailed instructions are available at [LinuxServer.io Jackett Docker](https://hub.docker.com/r/linuxserver/jackett/) 

## How to run Prowlarr service using Docker:

Detailed instructions are available at [Prowlarr Website](https://prowlarr.com/#downloads-v3-docker) 

## How to run Torrest service using Docker (optional):

1. Create a Dockerfile with the following content (make sure to check before the latest `VERSION` of the binary and your `OS` and `ARCH` and update accordingly).

```
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y curl unzip

ARG VERSION=0.0.5 OS=linux ARCH=x64

RUN curl -L https://github.com/i96751414/torrest-cpp/releases/download/v${VERSION}/torrest.${VERSION}.${OS}_${ARCH}.zip -o torrest.zip \
    && unzip torrest.zip -d /usr/local/lib \
    && rm torrest.zip

RUN chmod +x /usr/local/lib/torrest

CMD ["/usr/local/lib/torrest", "--log-level", "INFO"]
```

2. Build the Dockerfile

    docker build -t torrest-cpp .

3. Run the container on port 8080 (default port).
    
    docker run -p 8080:8080 --name torrest-service torrest-cpp

## Screenshots:

![](https://raw.githubusercontent.com/Sam-Max/plugin.video.jacktook/master/resources/screenshots/settings.png)

## Disclaimer:

This addon doesn't get sources by itself on torrent websites for legal reason and it should only be used to access movies and TV shows not protected by copyright.
