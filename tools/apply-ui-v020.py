"""Apply the original-art interface and after-story entry to the 0.1.0 reader."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
page = root / 'src/pages/index/index.ux'
text = page.read_text('utf8')
assert '<text class="title-text">星之终途</text>' in text
text = text.replace('<div class="page" onswipe="swipe">', '''<div class="page" onswipe="swipe">
    <image if="{{mode !== 'title' && mode !== 'play' && mode !== 'cg' && mode !== 'choice'}}" class="system-backdrop" src="/common/ui/system.png"></image>
    <div if="{{mode === 'title'}}" class="title-screen">
      <image class="title-art" src="/common/ui/title.jpg" onerror="backgroundError" oncomplete="backgroundLoaded"></image>
      <image class="title-logo" src="/common/ui/title-logo.png"></image>
      <div class="title-menu">
        <div class="title-row" onclick="startNew"><image class="title-label" src="/common/ui/title-start.png"></image></div>
        <div class="title-row" onclick="startAfterStory"><image class="title-label" src="/common/ui/title-after.png"></image></div>
        <div class="title-row" onclick="openChapterRoutes"><image class="title-label" src="/common/ui/title-chapter.png"></image></div>
        <div class="title-row" onclick="continueGame"><image class="title-label" src="/common/ui/title-load.png"></image></div>
        <div class="title-row" onclick="openSettings"><image class="title-label" src="/common/ui/title-config.png"></image></div>
        <div class="title-row" onclick="openGallery"><image class="title-label" src="/common/ui/title-extra.png"></image></div>
        <div class="title-row" onclick="exitApplication"><image class="title-label" src="/common/ui/title-exit.png"></image></div>
      </div>
      <text class="title-footer">STELLA OF THE END / AFTER STORY</text>
    </div>''')
start = text.index('    <div if="{{mode === \'title\'}}" class="title-panel">')
end = text.index('    <div if="{{mode === \'play\'}}" class="dialogue-panel">', start)
text = text[:start] + text[end:]
text = text.replace("mode === 'title' || mode === 'play'", "mode === 'play'")
text = text.replace('<div if="{{mode === \'play\'}}" class="dialogue-panel">', '''<div if="{{mode === 'play'}}" class="dialogue-panel">
      <image class="dialogue-texture" src="/common/ui/dialogue.png"></image>
      <div class="dialogue-edge"></div>''')
text = text.replace("hasNextChapter ? '#d5e5f2' : '#64758a'", "hasNextChapter ? '#ffffff' : '#a8bab3'")
text = text.replace("$item.occupied ? '#1d3549' : '#142535'", "$item.occupied ? '#dceae3' : '#edf3ef'")
text = text.replace('    <div if="{{mode === \'routes\' || mode === \'chapters\'}}" class="full-panel">', '''    <div if="{{mode === 'settings'}}" class="overlay">
      <text class="menu-title">CONFIG</text>
      <text class="panel-subtitle">阅读显示设置</text>
      <text class="menu-action" onclick="toggleSpeed">{{speedLabel}}</text>
      <text class="menu-action" onclick="toggleFont">{{fontLabel}}</text>
      <text class="menu-action muted" onclick="toTitle">返回标题</text>
    </div>
    <div if="{{mode === 'routes' || mode === 'chapters'}}" class="full-panel">''')
text = text.replace("startNew(){if(this.loading||!this._progressReady)return;", "startAfterStory(){if(this.loading||!this._progressReady)return;this.clearTyping();this._chapterSkip=null;this.session=withProgress(newState(catalog.afterInitial,true),this._progress);this.cachedChapter=0;this._autoHops=0;console.log('STELLA_RW5 after story start');this.renderFrame();},\n  openSettings(){if(this.loading)return;this.clearTyping();this.refreshSettings();this.mode='settings';},\n  exitApplication(){this._chapterSkip=null;this.clearTyping();this.loadSequence++;this._slotsSequence++;this._gallerySequence++;this.$app.exit();},\n  startNew(){if(this.loading||!this._progressReady)return;")
text = text.replace("openRoutes(){if(this.loading)return;this.clearTyping();this._browseRoute=0;", "openChapterRoutes(){if(this.loading)return;this.clearTyping();this._browseFromRoutes=true;this._browseRoute=0;this.mode='routes';this.browsePage=0;this.refreshBrowse();},\n  openRoutes(){if(this.loading)return;this.clearTyping();this._browseFromRoutes=false;this._browseRoute=0;")
text = text.replace('closeBrowse(){this.toTitle();}', "closeBrowse(){if(this.mode==='chapters'&&this._browseFromRoutes){this.mode='routes';this.browsePage=0;this.refreshBrowse();return;}this.toTitle();}")

css = '''
@font-face {font-family:stellaextra;src:url('/common/stella-extra.otf');}
.page{width:432px;height:514px;background-color:#f4f8f5;flex-direction:column;}
.system-backdrop{position:absolute;top:0px;left:0px;width:432px;height:514px;}
.title-screen{position:absolute;top:0px;left:0px;width:432px;height:514px;}
.title-art{position:absolute;top:0px;left:0px;width:432px;height:514px;object-fit:cover;}
.title-logo{position:absolute;top:26px;left:30px;width:352px;height:135px;object-fit:contain;}
.title-menu{position:absolute;top:214px;left:24px;width:250px;height:266px;flex-direction:column;}
.title-row{height:36px;width:246px;padding:0px 12px;justify-content:flex-start;align-items:center;}
.title-label{height:28px;width:222px;object-fit:contain;}
.title-footer{position:absolute;top:485px;left:38px;height:16px;width:330px;font-size:10px;color:#17483c;text-align:left;}
.art{position:absolute;top:0px;left:0px;width:432px;height:286px;justify-content:center;align-items:center;background-color:#edf3f0;}
.background{width:432px;height:286px;object-fit:contain;}
.body{position:absolute;top:0px;left:116px;width:200px;height:286px;object-fit:contain;}
.dialogue-panel{position:absolute;top:286px;left:0px;width:432px;height:228px;flex-direction:column;padding:12px 18px;background-color:#073d37;}
.dialogue-texture{position:absolute;top:0px;left:0px;width:432px;height:228px;object-fit:cover;}
.dialogue-edge{position:absolute;top:0px;left:18px;width:396px;height:2px;background-color:#e1f6ef;}
.speaker-row{height:30px;justify-content:space-between;align-items:center;}
.speaker{font-size:23px;color:#ffffff;}
.chapter{font-size:16px;color:#e0f0e9;}
.dialogue-scroll{width:396px;height:128px;}
.dialogue{width:396px;color:#ffffff;line-height:34px;}
.toolbar{height:42px;width:396px;justify-content:space-between;align-items:center;}
.tool{font-size:20px;color:#ffffff;padding:8px;}
.game-title{font-size:28px;color:#174d40;text-align:left;margin-bottom:12px;}
.subtitle{font-size:20px;color:#527769;text-align:left;margin-bottom:24px;}
.action{height:52px;width:356px;margin-bottom:8px;color:#ffffff;background-color:#21594d;text-align:center;font-size:24px;}
.choice-panel{position:absolute;top:0px;left:0px;width:432px;height:514px;background-color:#123f36;flex-direction:column;padding:24px 18px;}
.choice-title{height:44px;font-size:25px;color:#ffffff;margin-bottom:14px;text-align:left;}
.choice-list{width:396px;height:370px;flex-direction:column;}
.choice{height:108px;width:396px;padding:16px;background-color:#2c6657;font-size:24px;line-height:32px;color:#ffffff;text-align:left;margin-bottom:10px;}
.small-action{height:38px;font-size:20px;color:#ffffff;text-align:center;}
.overlay{position:absolute;top:0px;left:0px;width:432px;height:514px;flex-direction:column;padding:22px 32px;}
.menu-title{height:40px;font-size:28px;color:#174d40;text-align:left;margin-bottom:12px;}
.menu-action{height:50px;font-size:22px;color:#ffffff;background-color:#21594d;margin-bottom:8px;text-align:center;}
.muted{color:#325e4e;background-color:#dae8df;}
.full-panel{position:absolute;top:0px;left:0px;width:432px;height:514px;flex-direction:column;padding:16px 18px;}
.panel-title{height:36px;font-size:28px;color:#174d40;text-align:left;margin-bottom:4px;}
.panel-subtitle{height:22px;font-size:16px;color:#527769;text-align:left;margin-bottom:6px;}
.slot-list{height:368px;width:396px;flex-direction:column;}
.slot-card{height:84px;width:396px;margin-bottom:8px;padding:7px 12px;flex-direction:column;background-color:#e6efe9;}
.slot-title{height:26px;font-size:22px;color:#173f35;}
.slot-meta{height:19px;font-size:16px;color:#527769;}
.slot-preview{height:22px;font-size:18px;color:#345f4f;}
.pager{height:44px;width:396px;justify-content:space-between;align-items:center;}
.pager-action{font-size:20px;color:#24594c;padding:8px;}
.gallery-row{height:184px;width:396px;justify-content:space-between;}
.gallery-card{height:176px;width:192px;padding:6px;flex-direction:column;background-color:#e5eee8;}
.gallery-thumb{height:116px;width:180px;object-fit:contain;background-color:#f5f8f5;}
.gallery-caption{height:48px;width:180px;font-size:18px;line-height:22px;color:#234f40;text-align:center;}
.cg-panel{position:absolute;top:0px;left:0px;width:432px;height:514px;flex-direction:column;background-color:#f1f6f1;}
.cg-image{width:432px;height:432px;object-fit:contain;}
.cg-caption{width:432px;height:28px;font-size:18px;color:#234f40;text-align:center;}
.cg-controls{width:432px;height:54px;padding:0px 10px;justify-content:space-between;align-items:center;background-color:#e5eee8;}
.end-panel{position:absolute;top:0px;left:0px;width:432px;height:514px;flex-direction:column;padding:160px 38px 24px;}
.confirm-text{font-size:24px;color:#234f40;margin:30px 0px;}
.error-text{font-size:22px;color:#945746;margin-bottom:30px;}
.loading{position:absolute;top:234px;left:128px;width:176px;height:46px;text-align:center;font-size:23px;color:#ffffff;background-color:#21594d;}
'''
text = text[:text.index('<style>')] + '<style>' + css + '</style>\n'
page.write_text(text, 'utf8')
manifest_path = root / 'src/manifest.json'
manifest = json.loads(manifest_path.read_text('utf8'))
manifest.update(versionName='0.2.0', versionCode=2)
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', 'utf8')
package_path = root / 'package.json'
package = json.loads(package_path.read_text('utf8'))
package['version'] = '0.2.0'
package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + '\n', 'utf8')
print('UI and AFTER STORY applied to version 0.2.0.')
