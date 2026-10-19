// Local-first demo store. Every record is generated in this browser and
// persisted to localStorage; no meeting, AI, device or payment service is used.
export const STORAGE_KEY = 'effmeet2.local.v1';
export const SCHEMA_VERSION = 3;

export const DEVICES = [
  {key:'phone', label:'本机手机', detail:'摄像头 + 麦克风', camera:true},
  {key:'external', label:'外接摄像头', detail:'模拟设备', camera:true},
  {key:'mic', label:'仅麦克风', detail:'无摄像头', camera:false}
];

export const DEFAULT_SETTINGS = {
  reminders:true,
  sounds:true,
  reduceMotion:false,
  device:'phone',
  language:'zh'
};

export const PLANS = {
  free: {
    key: 'free',
    label: '免费版',
    quotaTotal: 120,
    maxMeeting: 60,
    history: '30 天',
    analysis: false,
    rows: [
      ['每月额度', '120 分钟'],
      ['单次会议', '60 分钟'],
      ['历史保存', '30 天'],
      ['高级分析', '—']
    ]
  },
  pro: {
    key: 'pro',
    label: '高级版',
    quotaTotal: 600,
    maxMeeting: 180,
    history: '永久',
    analysis: true,
    rows: [
      ['每月额度', '600 分钟'],
      ['单次会议', '180 分钟'],
      ['历史保存', '永久'],
      ['高级分析', '支持']
    ]
  }
};

const PEOPLE = {
  lin: {name:'林小满', role:'线上', color:'#6F8564', tint:'#EDF2EA'},
  zhou:{name:'周航',   role:'现场', color:'#5F7396', tint:'#E9EEF5'},
  chen:{name:'陈可',   role:'现场', color:'#A37462', tint:'#F6ECE7'},
  xu:  {name:'许老师', role:'现场', color:'#816E96', tint:'#F1ECF5'},
  wang:{name:'王助教', role:'现场', color:'#9A8455', tint:'#F5F0E4'}
};

function participant(key, nickname) {
  const base = PEOPLE[key];
  const name = key === 'lin' && nickname ? nickname : base.name;
  return {id:'p-' + key, name, short:name.slice(0, 1), role:base.role, color:base.color, tint:base.tint};
}

function participants(keys, nickname) {
  return keys.map(key => participant(key, nickname));
}

function daysAgo(days, hour, minute) {
  const date = new Date();
  date.setDate(date.getDate() - days);
  date.setHours(hour, minute, 0, 0);
  return date;
}

function resetDate() {
  const date = new Date();
  date.setMonth(date.getMonth() + 1, 1);
  date.setHours(0, 0, 0, 0);
  const pad = value => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function seedMeetings() {
  const weeklyStart = daysAgo(1, 16, 12);
  const weeklyEnd = daysAgo(1, 16, 40);
  const purchaseStart = daysAgo(3, 10, 15);
  const purchaseEnd = daysAgo(3, 10, 50);
  const proposalStart = daysAgo(7, 15, 20);
  const proposalEnd = daysAgo(7, 15, 56);

  return [
    {
      id:'m-weekly',
      title:'课程项目周会',
      status:'ended',
      isDemo:false,
      source:'history',
      startedAt:weeklyStart.toISOString(),
      endedAt:weeklyEnd.toISOString(),
      durationMin:28,
      participants:participants(['lin','zhou','chen'], '林小满'),
      summary:'本周完成回收箱结构草图与材料清单，确定下周制作手板；展示脚本和分工仍需补齐。',
      conclusions:[
        '结构草图已定稿，进入手板准备。',
        '展示脚本按“问题—方案—验证”三段重写。',
        '下周三前提交材料采购清单。'
      ],
      todos:[
        {id:'wt1', text:'提交材料采购清单', owner:'陈可', done:false},
        {id:'wt2', text:'重写展示脚本三段结构', owner:'林小满', done:true},
        {id:'wt3', text:'预约创客空间打印手板', owner:'周航', done:false}
      ],
      viewpoints:[
        {id:'wv1', topic:'进度安排', speakerId:'p-zhou', text:'手板最好下周中之前打出来，留出修改时间。', status:'responded', evidenceIds:['wu2'], responseEvidenceIds:['wu3']},
        {id:'wv2', topic:'展示材料', speakerId:'p-lin', text:'展示脚本现在太像说明书，应该先讲问题再讲方案。', status:'responded', evidenceIds:['wu4'], responseEvidenceIds:['wu5']},
        {id:'wv3', topic:'分工', speakerId:'p-chen', text:'采购清单和打印预约可以并行，不用等结构完全定稿。', status:'uncertain', evidenceIds:['wu6']}
      ],
      transcript:[
        {id:'wu1', speakerId:'p-lin', at:'16:12', text:'今天主要对齐三件事：结构、展示材料、下周分工。'},
        {id:'wu2', speakerId:'p-zhou', at:'16:18', text:'手板最好下周中之前打出来，留出修改时间。'},
        {id:'wu3', speakerId:'p-lin', at:'16:21', text:'可以，打印预约我来跟进。'},
        {id:'wu4', speakerId:'p-lin', at:'16:26', text:'展示脚本现在太像说明书，应该先讲问题再讲方案。'},
        {id:'wu5', speakerId:'p-zhou', at:'16:29', text:'同意，按问题、方案、验证三段改。'},
        {id:'wu6', speakerId:'p-chen', at:'16:34', text:'采购清单和打印预约可以并行，不用等结构完全定稿。'}
      ],
      capture:{src:'assets/capture-sketch.svg', description:'回收箱结构草图：折叠方式与三格分区。', at:'16:14'},
      aiPrompt:null
    },
    {
      id:'m-purchase',
      title:'实验室设备采购',
      status:'ended',
      isDemo:false,
      source:'history',
      startedAt:purchaseStart.toISOString(),
      endedAt:purchaseEnd.toISOString(),
      durationMin:35,
      participants:participants(['lin','xu','wang','chen'], '林小满'),
      summary:'确认优先更换主控板，热成像仪先向学院借用；本周内完成下单，预算表同步更新。',
      conclusions:[
        '先更换主控板，热成像仪短期借用。',
        '本周内完成主控板与传感器下单。',
        '预算表由林小满更新后再确认。'
      ],
      todos:[
        {id:'pt1', text:'本周内下单主控板', owner:'陈可', done:false},
        {id:'pt2', text:'向学院申请借用热成像仪', owner:'王助教', done:true},
        {id:'pt3', text:'更新设备预算表', owner:'林小满', done:false}
      ],
      viewpoints:[
        {id:'pv1', topic:'采购顺序', speakerId:'p-lin', text:'主控板已经不够用了，先换主控。', status:'responded', evidenceIds:['pu2'], responseEvidenceIds:['pu4']},
        {id:'pv2', topic:'预算', speakerId:'p-xu', text:'预算主要留给主控和传感器。', status:'responded', evidenceIds:['pu4'], responseEvidenceIds:['pu5']},
        {id:'pv3', topic:'交期', speakerId:'p-chen', text:'供应商说主控要两周，最好这周下单。', status:'possibly_unresponded', evidenceIds:['pu5']},
        {id:'pv4', topic:'预算', speakerId:'p-chen', text:'超支部分最好提前和老师确认。', status:'no_analysis', evidenceIds:[]}
      ],
      transcript:[
        {id:'pu1', speakerId:'p-xu', at:'10:15', text:'这轮先买热成像仪还是先换主控板？'},
        {id:'pu2', speakerId:'p-lin', at:'10:18', text:'主控板已经不够用了，先换主控。'},
        {id:'pu3', speakerId:'p-wang', at:'10:22', text:'热成像仪可以借用学院的，短期不用买。'},
        {id:'pu4', speakerId:'p-xu', at:'10:27', text:'那预算主要留给主控和传感器。'},
        {id:'pu5', speakerId:'p-chen', at:'10:33', text:'供应商说主控要两周，最好这周下单。'}
      ],
      capture:null,
      aiPrompt:null
    },
    {
      id:'m-proposal',
      title:'开题报告讨论',
      status:'ended',
      isDemo:false,
      source:'history',
      startedAt:proposalStart.toISOString(),
      endedAt:proposalEnd.toISOString(),
      durationMin:36,
      participants:participants(['lin','zhou','xu'], '林小满'),
      summary:'研究问题聚焦到“线上成员如何被现场听见”，方法以访谈和原型测试为主，时间线压缩到六周。',
      conclusions:[
        '研究问题收敛为一个核心问题。',
        '方法采用半结构访谈 + 两轮原型测试。',
        '六周内完成首轮访谈与测试。'
      ],
      todos:[
        {id:'ot1', text:'整理首轮访谈提纲', owner:'林小满', done:false},
        {id:'ot2', text:'联系两位远程成员参与测试', owner:'周航', done:false},
        {id:'ot3', text:'更新六周时间线', owner:'许老师', done:true}
      ],
      viewpoints:[
        {id:'ov1', topic:'研究问题', speakerId:'p-xu', text:'问题不要铺太大，先回答线上成员为什么插不上话。', status:'responded', evidenceIds:['ou2'], responseEvidenceIds:['ou3']},
        {id:'ov2', topic:'研究方法', speakerId:'p-lin', text:'访谈和原型测试可以穿插做，不必等访谈全部结束。', status:'responded', evidenceIds:['ou4'], responseEvidenceIds:['ou5']},
        {id:'ov3', topic:'时间线', speakerId:'p-zhou', text:'六周有点紧，测试至少留两周。', status:'uncertain', evidenceIds:['ou6']}
      ],
      transcript:[
        {id:'ou1', speakerId:'p-lin', at:'15:20', text:'今天想把研究问题和六周安排定下来。'},
        {id:'ou2', speakerId:'p-xu', at:'15:24', text:'问题不要铺太大，先回答线上成员为什么插不上话。'},
        {id:'ou3', speakerId:'p-lin', at:'15:27', text:'同意，我把问题收敛到一个核心。'},
        {id:'ou4', speakerId:'p-lin', at:'15:32', text:'访谈和原型测试可以穿插做，不必等访谈全部结束。'},
        {id:'ou5', speakerId:'p-xu', at:'15:35', text:'可以，但每轮测试要有明确记录。'},
        {id:'ou6', speakerId:'p-zhou', at:'15:40', text:'六周有点紧，测试至少留两周。'}
      ],
      capture:null,
      aiPrompt:null
    }
  ];
}

export function seedDB() {
  return {
    schemaVersion: SCHEMA_VERSION,
    user: {
      nickname:'林小满',
      plan:'free',
      quotaTotal:PLANS.free.quotaTotal,
      quotaUsed:38,
      quotaReset:resetDate()
    },
    device: {connected:true, battery:76},
    settings: {...DEFAULT_SETTINGS},
    meetings: seedMeetings(),
    demoMeetings: [],
    scheduled: [],
    active: null
  };
}

export function loadDB() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && parsed.schemaVersion === SCHEMA_VERSION && Array.isArray(parsed.meetings)) {
        parsed.settings = {...DEFAULT_SETTINGS, ...(parsed.settings || {})};
        if (parsed.active && !parsed.active.device) parsed.active.device = parsed.settings.device;
        return parsed;
      }
      if (parsed && parsed.schemaVersion === 2 && Array.isArray(parsed.meetings)) {
        parsed.schemaVersion = SCHEMA_VERSION;
        parsed.settings = {...DEFAULT_SETTINGS, ...(parsed.settings || {})};
        if (parsed.active && !parsed.active.device) parsed.active.device = parsed.settings.device;
        delete parsed.ui;
        persist(parsed);
        return parsed;
      }
    }
  } catch {
    // A malformed local record falls back to a fresh seed.
  }
  const db = seedDB();
  persist(db);
  return db;
}

export function persist(db) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(db));
  } catch {
    // Storage can be unavailable in private mode; the session still works.
  }
}

export function resetDB() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore unavailable storage.
  }
  const db = seedDB();
  persist(db);
  return db;
}

export function remainingMinutes(db) {
  return Math.max(0, db.user.quotaTotal - db.user.quotaUsed);
}

export function setPlan(db, planKey) {
  const plan = PLANS[planKey];
  if (!plan) return db;
  db.user.plan = planKey;
  db.user.quotaTotal = plan.quotaTotal;
  db.user.quotaUsed = Math.min(db.user.quotaUsed, plan.quotaTotal);
  persist(db);
  return db;
}

export function activeMeeting(db, options = {}) {
  const nickname = db.user.nickname;
  const team = participants(['lin', 'zhou', 'chen', 'xu'], nickname);
  const startedAt = new Date(Date.now() - 42 * 60000).toISOString();
  const prompt = {
    id:'c1',
    viewpointId:'v1',
    text:'满溢检测的话，用重量传感器比摄像头便宜很多，而且不用处理隐私问题。',
    evidenceIds:['t2'],
    state:'awaiting_confirmation',
    expiresAt:Date.now() + 120000,
    createdAt:Date.now()
  };

  const meeting = {
    id:'m-live-' + Date.now(),
    title:options.title || '回收箱方案评审',
    status:'live',
    isDemo:Boolean(options.isDemo),
    source:options.source || 'quick',
    code:options.code || '',
    device:options.device || db.settings.device || 'phone',
    startedAt,
    endedAt:null,
    durationMin:0,
    participants:team,
    summary:'围绕三格回收箱的折叠结构、满溢检测与投放口高度展开。现场认可重量传感器方向，投放口高度需按低年级学生复核，结构与开模成本仍待确认。',
    conclusions:[
      '满溢检测采用重量传感器，不使用摄像头。',
      '投放口高度按低年级平均身高重新测量。',
      '先制作手板验证折叠结构，再决定是否开模。'
    ],
    todos:[
      {id:'lt1', text:'测量一至三年级平均身高，更新投放口高度', owner:'周航', done:false},
      {id:'lt2', text:'出重量传感器安装位置草图', owner:nickname, done:false},
      {id:'lt3', text:'补充手板预算与开模费用', owner:'许老师', done:false}
    ],
    viewpoints:[
      {id:'v1', topic:'满溢检测', speakerId:'p-lin', text:'满溢检测的话，用重量传感器比摄像头便宜很多，而且不用处理隐私问题。', status:'possibly_unresponded', evidenceIds:['t2']},
      {id:'v2', topic:'结构强度', speakerId:'p-zhou', text:'折叠的结构强度够不够？回收箱会被撞变形。', status:'uncertain', evidenceIds:['t1']},
      {id:'v3', topic:'投放口高度', speakerId:'p-lin', text:'投放口的高度要照顾小学生，别按成年人身高设计。', status:'responded', evidenceIds:['t4'], responseEvidenceIds:['t5']},
      {id:'v4', topic:'连接件', speakerId:'p-chen', text:'折叠箱体的连接件可以用卡扣，拆装方便。', status:'possibly_unresponded', evidenceIds:['t3']},
      {id:'v5', topic:'成本与开模', speakerId:'p-xu', text:'预算里还要留出模具修改的费用。', status:'responded', evidenceIds:['t6'], responseEvidenceIds:['t7']},
      {id:'v6', topic:'成本与开模', speakerId:'p-chen', text:'那就先做一版手板，再决定开模。', status:'responded', evidenceIds:['t7']},
      {id:'v7', topic:'状态提示', speakerId:'p-xu', text:'箱门上的屏幕可以显示是否满溢。', status:'no_analysis', evidenceIds:[]}
    ],
    transcript:[
      {id:'t1', speakerId:'p-zhou', at:'38:12', text:'折叠的结构强度够不够？回收箱会被撞变形。'},
      {id:'t2', speakerId:'p-lin', at:'38:48', text:'满溢检测的话，用重量传感器比摄像头便宜很多，而且不用处理隐私问题。'},
      {id:'t3', speakerId:'p-chen', at:'39:35', text:'折叠箱体的连接件可以用卡扣，拆装方便。'},
      {id:'t4', speakerId:'p-lin', at:'40:10', text:'投放口的高度要照顾小学生，别按成年人身高设计。'},
      {id:'t5', speakerId:'p-zhou', at:'40:26', text:'这个我们量一下，按低年级平均身高来。'},
      {id:'t6', speakerId:'p-xu', at:'41:02', text:'预算里还要留出模具修改的费用。'},
      {id:'t7', speakerId:'p-chen', at:'41:20', text:'那就先做一版手板，再决定开模。'}
    ],
    capture:{src:'assets/capture-sketch.svg', description:'三格回收箱正面，顶部投放口，右上「满溢检测？」', at:'41:24'},
    aiPrompt:prompt
  };

  db.active = meeting;
  persist(db);
  return meeting;
}

export function endActiveMeeting(db) {
  const active = db.active;
  if (!active) return null;
  const endedAt = new Date();
  const durationMin = Math.max(1, Math.round((endedAt - new Date(active.startedAt)) / 60000));
  const record = {
    ...active,
    status:'ended',
    endedAt:endedAt.toISOString(),
    durationMin,
    aiPrompt:active.aiPrompt ? {...active.aiPrompt} : null
  };
  db.active = null;
  if (record.isDemo) {
    db.demoMeetings.unshift(record);
  } else {
    db.meetings.unshift(record);
    db.user.quotaUsed = Math.min(db.user.quotaTotal, db.user.quotaUsed + durationMin);
  }
  persist(db);
  return record;
}

export function findMeeting(db, id) {
  return db.meetings.find(item => item.id === id) || db.demoMeetings.find(item => item.id === id) || null;
}

export function updateTodo(db, meetingId, todoId, done) {
  const meeting = findMeeting(db, meetingId);
  if (!meeting) return null;
  const todo = meeting.todos.find(item => item.id === todoId);
  if (!todo) return null;
  todo.done = Boolean(done);
  persist(db);
  return todo;
}

export function addScheduled(db, record) {
  db.scheduled.push(record);
  db.scheduled.sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time));
  persist(db);
  return record;
}

export function removeScheduled(db, id) {
  db.scheduled = db.scheduled.filter(item => item.id !== id);
  persist(db);
}

export function speakerOf(meeting, speakerId) {
  return meeting.participants.find(item => item.id === speakerId) || {
    id:speakerId, name:'未知发言者', short:'?', role:'现场', color:'#8A8377', tint:'#F1EEE7'
  };
}

export function viewpointStateLabel(status) {
  return {
    responded:'已回应',
    possibly_unresponded:'可能未回应',
    uncertain:'需核对',
    no_analysis:'未分析'
  }[status] || '待核对';
}
