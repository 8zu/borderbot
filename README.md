# borderちゃん

Discord 用ミリシタボーダー告知 bot です。

## インストール

[https://discordapp.com/api/oauth2/authorize?client_id=398096825061474305&permissions=10240&scope=bot](このリンク)をクリック！入れたいサーバーを選択する。

## 使い方

!help                      命令説明
!add_channel #channel      チャネルを告知リストに追加する
!remove_channel #channel   告知リストからチャネルをリムーブする
!border <id>               最新のイベントボーダーを表示する・またイベントIDで選択したイベントのボーダーを表示する
  
イベント期間、botが告知リストにあるチャンネルに、半時間の頻度でボーダーを告知する、テンプレート：

```
イベント名
<開始時間>～<終了時間>, あと O 日 X 時間

<現在時間>
1位：       2,324,615 (+23,628)
2位：       1,758,877 (+23,628)
3位：       1,424,927 (+4,165)
100位：       306,343 (+3,671)
2000位：       63,199 (+1,140)
5000位：       36,913 (+330)
10000位：      27,675 (+361)
20000位：      20,094 (+286)
50000位：       9,756 (+219)
100000位：        884 (+11)
```

## アップデート

これからの仕様追加予定

- [] 起動時アップデート
- [] イベント最終ボーダーをゲット
- [] オーナーだけが使える管理コマンド（キャッシュクリーン）
- [] グラフ表示（！）
