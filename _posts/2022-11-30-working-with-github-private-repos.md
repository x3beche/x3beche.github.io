---
layout: post
title: Working With Github Private Repos
description: Working With Github Private Repos
summary: Working With Github Private Repos
tags: github repostory private
minute: 5
---

# downloading private repo
```
git clone https://<ACCESS_TOKEN>@github.com/<USERNAME>/<REPOSTORY_NAME>.git
```

# changing for installed private repo
```
git config user.name "x3beche"
git config user.email "x3beche@gmail.com"
git remote remove origin
git remote add origin https://<TOKEN>@github.com/<USERNAME>/<REPO>.git
git push --set-upstream origin main
```