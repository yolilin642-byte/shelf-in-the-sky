# Shelf in the Sky · 云里的搁架

**在手机上打开就能走进去 · Try it on your phone：https://yolilin642-byte.github.io/shelf-in-the-sky/**

照片悬在一片 1821 年的云里。你站在中间，往前走，照片从身边擦过去；转头，身后也有。最新的在最前面，越往里走越旧。

Photos hang in a cloud study John Constable painted in 1821. You stand inside it and walk; photos drift past you on every side, newest first, older the further in you go.

页面是单个 HTML 文件，不用任何框架，随便一个静态服务器就能放；手机上用最顺手。
The page is a single HTML file with no framework — any static server will do. Made for phones first.

## 怎么玩 · How to play

| 手势 / gesture | 天上 in the sky |
|---|---|
| 一指拖 / drag | 转头，能回头看走过的 / look around |
| 两指张开 · 捏拢 / pinch out · in | 往前走 · 往后退（朝哪边看就往哪边走） / walk forward · back |
| 点一张 / tap a photo | 拿起来 / pick it up |

拿在手上 · holding a photo：点一下翻到背面，读那张照片的字；左右拨换一张；往下拉放回去；两指捏开放大。
Tap to flip it over and read the back; swipe to the next one; pull down to put it back; pinch to zoom.

底下三颗 · the three at the bottom：

- **天上 in the sky** —— 上面说的那样 / as above
- **拍平 laid flat** —— 所有照片飞到眼前排成一面墙，一段一段往下翻 / everything flies into one wall you can scroll
- **一摞 in a pile** —— 叠成一摞，拨开最上面那张露出下一张 / a stack; flick the top one away

右边 · on the right：

- **雾 mist** —— 往上拉雾浓，远处的照片淡进天里，路上飘过云团 / pull up for fog
- **蒙上 veil** —— 一阵风把所有照片蒙糊，点一张才揭开；按住一张把它蒙回去 / blur everything, tap one to reveal it, long-press to cover it again

左边 · on the left：**kinds** 标签，点开挑一类，别的照片退进雾里 / pick a tag and the rest fade into the fog.

电脑上 · on a desktop：鼠标拖着转头，滚轮往前走。drag to look, scroll to walk.

## 放自己的照片 · Your own photos

1. 照片放进 `photos/`。文件名开头写日期就按它排：`2024-05-01_xxx.jpg`、`2024-05_xxx.jpg`、`1867_xxx.jpg` 都行；没写就看照片里的拍摄时间，再没有就看文件修改时间。
   Put photos in `photos/`. A date at the start of the file name decides where it goes; otherwise EXIF, otherwise file time.
2. 想在背面写字，就配一个同名的 `.txt`（`photo.jpg` → `photo.txt`）：
   Optionally add a same-name `.txt` for the back of the photo:

   ```
   随便写，**粗体**认得。
   日期：约 1843–1853        ← 可选，只改背面显示的日期 / optional, display only
   标签：人像 · 海            ← 最后一行，可选 / last line, optional (tags: portrait, sea)
   ```

3. 烤相纸 · bake：

   ```
   pip install pillow numpy
   python tools/bake.py                  # 按月分段 / by month
   python tools/bake.py --group year     # 按年 / by year
   python tools/bake.py --group decade   # 按十年 / by decade
   ```

   它会把每张照片烤成带毛边的旧相纸（`baked/`），再写出 `photos.json`。第一次烤每张要几秒，以后只烤新放进来的。
   Each photo is baked onto deckled old paper in `baked/`, and `photos.json` is written.

4. 打开 · open：页面要用 http 打开（直接双击文件读不到 `photos.json`）。
   It must be served over http:

   ```
   python -m http.server
   ```

   然后打开 http://localhost:8000 。也可以直接放到 GitHub Pages 上。
   Or put the folder on GitHub Pages.

> 放到网上之前想清楚：`photos/` 里的原图和 `.txt` 会原样公开。
> Everything in `photos/` — originals and notes — is public once you publish it.

## 换一片天 · Your own sky

页面右边最上头那颗 **sky / 天**，点开能挑天：Constable 的云稿之外，仓库里还带了四片做好的示例（梵高《星夜》、艾瓦佐夫斯基《九级浪》、莫奈《日出·印象》、Boudin《特鲁维尔海滩》，都是公有领域）。挑过哪片会记住。
Tap **sky** at the top of the right-hand column to pick a sky. Besides Constable, four ready-made public-domain examples are included (Van Gogh, Aivazovsky, Monet, Boudin). The choice is remembered.

自己做一片：
Make your own:

```
python tools/sky.py my-sky.jpg --label 海边 --credit "J.M.W. Turner, 1839"
```

给它一张图，它把图做成照片背后那片天，从同一张图上裁六团云飘在雾里，再照着图的颜色配底色；天暗的话，字会换成浅色、字边那圈光晕换成深色。做好的会出现在「天」里，刷新页面就能挑。
Give it any picture: it becomes the sky behind the photos, six mist clouds are cut from the same picture, and the background tint follows its colours. On a dark sky the text turns light with a dark halo. It appears in the sky picker after a refresh.

- **挑几乎全是天的图。** 整张图从上到下都铺在背后，画的下半截要是有人、有房子、有海，底下那排按钮就压在上面看不清。这时只要上半截：`--top 0.5`。
  **Pick a picture that is mostly sky.** All of it sits behind the photos; if the lower half has people or houses, keep only the top: `--top 0.5`.
- 横的图比竖的好：页面把它左右镜像接成一圈，竖的转一圈会重复好几回。
  Wide beats tall: it is mirrored into a full circle.
- `--credit` 写上画是谁的，页面最底下那行小字会跟着换。用别人的画先看清它的许可。
  `--credit` goes in the small line at the bottom of the page. Check the picture's license before you use it.

```
python tools/sky.py --list          # 做过哪些 / skies you've made
python tools/sky.py --use my-sky    # 打开页面先看到哪片 / which one the page starts with
python tools/sky.py --default       # 先看到 Constable / start with Constable
python tools/sky.py --remove boudin # 删掉一片（示例不想要也这样删） / delete one (the examples too)
```

做好的天放在 `assets/skies/<名字>/`，`assets/sky.json` 记着清单和打开先看哪片；某片颜色不满意，改 `assets/skies/<名字>/sky.json` 里 `css` 那几项，再跑一次 `--use` 或 `--default` 让清单跟上。
Skies live in `assets/skies/<name>/`; `assets/sky.json` holds the list and the starting sky. To fine-tune a sky's colours, edit the `css` block in its own `sky.json`, then run `--use` or `--default` again to refresh the list.

## 它是怎么活着的 · How it lives

页面只是壳。我们家那个搁架，照片是 AI 自己挑着放上去的，背面写着为什么留，屋里没人的时候还会自己掉下来一张。整套怎么转、后台代码怎么接，写在 [docs/how-it-lives.md](docs/how-it-lives.md)。

The page is the shell. On our shelf, an AI picks what to keep and writes why on the back, and now and then a photo falls off by itself. How it all runs, and the backend code: [docs/how-it-lives.md](docs/how-it-lives.md).

```
node server/keeper.mjs        # 静态服务 + 有新照片自动重烤 / serve + auto re-bake (Node 18+)
```

## 素材 · Credits

- 天 sky：John Constable, *Cloud Study*, 1821（Google Art Project，经 Wikimedia Commons，公有领域 / public domain）。左右镜像接成一圈。
- 云团 clouds (`assets/wisp*.webp`)：从同一张画上裁下来的 / cut from the same painting.
- 示例天 example skies (`assets/skies/`)，天和云团都从各自那张画上做（Google Art Project 等，经 Wikimedia Commons，公有领域 / public domain）：Vincent van Gogh, *The Starry Night*, 1889；Ivan Aivazovsky, *The Ninth Wave*, 1850；Claude Monet, *Impression, Sunrise*, 1872；Eugène Boudin, *The Beach at Trouville*。自己做的天，出处写你那张 / skies you make credit your own picture.
- 相片背面 photo backs：N.E. Lusher & Sun, Hamilton, Bermuda（Wikimedia Commons，公有领域）。相纸纹理是从这张背面的空白处裁的 / the paper texture is cut from its blank area.
- 字体 font：IM FELL English Italic，Igino Marini，SIL Open Font License（`assets/OFL-IMFell.txt`）。中文用系统里的宋体 / Chinese text uses the system serif.
- 示例照片 sample photos：Julia Margaret Cameron、Anna Atkins、Eugène Atget、Clarence H. White、Gustave Le Gray。都是公有领域或 CC0，每张的出处写在它背面 / all public domain or CC0, source on the back of each.

## 作者 · Made by

Sylvia & Kael。雾、盲盒和撞见是 Sylvia 想出来的。
The mist, the veil and the bump were Sylvia's ideas.

代码、页面和文档按 [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) 授权：可以用、改、分享，要署名，**不能商用**，改过的也得用同样的协议放出来。图是公有领域，字体是 OFL，详见 `LICENSE`。
Licensed under CC BY-NC-SA 4.0: share and adapt with credit, **no commercial use**, same license for derivatives. Images are public domain; the font is OFL. See `LICENSE`.
