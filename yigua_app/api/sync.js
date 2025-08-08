// Vercel Serverless Function - 数据同步
// 支持上传和下载用户数据

const { createClient } = require('@supabase/supabase-js');

// 初始化Supabase客户端
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY
);

// 验证用户令牌（简单的JWT验证）
async function verifyToken(token) {
  if (!token) return null;
  
  try {
    // 使用Supabase的内置认证
    const { data: { user }, error } = await supabase.auth.getUser(token);
    if (error) throw error;
    return user;
  } catch (error) {
    // 如果没有启用Supabase Auth，使用简单的令牌验证
    // 这里可以替换为您自己的验证逻辑
    if (token === process.env.SYNC_SECRET_TOKEN) {
      return { id: 'anonymous', email: 'user@example.com' };
    }
    return null;
  }
}

module.exports = async (req, res) => {
  // 设置CORS头
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  // 处理OPTIONS请求
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // 验证用户身份
  const token = req.headers.authorization?.replace('Bearer ', '');
  const user = await verifyToken(token);

  if (!user && process.env.REQUIRE_AUTH === 'true') {
    return res.status(401).json({ 
      error: 'Unauthorized',
      message: 'Please provide a valid authentication token' 
    });
  }

  const userId = user?.id || 'anonymous';

  try {
    switch (req.method) {
      case 'GET':
        // 获取用户数据
        const { type = 'all' } = req.query;
        
        let data = {};
        
        if (type === 'all' || type === 'history') {
          // 获取历史记录
          const { data: history, error } = await supabase
            .from('user_history')
            .select('*')
            .eq('user_id', userId)
            .order('created_at', { ascending: false })
            .limit(100);
          
          if (!error) data.history = history;
        }
        
        if (type === 'all' || type === 'favorites') {
          // 获取收藏
          const { data: favorites, error } = await supabase
            .from('user_favorites')
            .select('*')
            .eq('user_id', userId)
            .order('created_at', { ascending: false });
          
          if (!error) data.favorites = favorites;
        }
        
        if (type === 'all' || type === 'settings') {
          // 获取设置
          const { data: settings, error } = await supabase
            .from('user_settings')
            .select('*')
            .eq('user_id', userId)
            .single();
          
          if (!error) data.settings = settings;
        }
        
        return res.status(200).json({
          success: true,
          userId,
          data,
          timestamp: new Date().toISOString()
        });

      case 'POST':
      case 'PUT':
        // 上传/更新用户数据
        const { type: uploadType, data: uploadData } = req.body;
        
        if (!uploadType || !uploadData) {
          return res.status(400).json({ 
            error: 'Missing required fields',
            message: 'Please provide type and data' 
          });
        }
        
        let result = {};
        
        switch (uploadType) {
          case 'history':
            // 保存历史记录
            const { data: historyResult, error: historyError } = await supabase
              .from('user_history')
              .insert({
                user_id: userId,
                type: uploadData.type,
                content: uploadData.content,
                result: uploadData.result,
                created_at: new Date().toISOString()
              });
            
            if (historyError) throw historyError;
            result = historyResult;
            break;
            
          case 'favorite':
            // 添加收藏
            const { data: favResult, error: favError } = await supabase
              .from('user_favorites')
              .upsert({
                user_id: userId,
                item_id: uploadData.item_id,
                type: uploadData.type,
                content: uploadData.content,
                created_at: new Date().toISOString()
              });
            
            if (favError) throw favError;
            result = favResult;
            break;
            
          case 'settings':
            // 更新设置
            const { data: settingsResult, error: settingsError } = await supabase
              .from('user_settings')
              .upsert({
                user_id: userId,
                ...uploadData,
                updated_at: new Date().toISOString()
              });
            
            if (settingsError) throw settingsError;
            result = settingsResult;
            break;
            
          case 'batch':
            // 批量同步
            const results = {};
            
            if (uploadData.history) {
              const { data: h, error: he } = await supabase
                .from('user_history')
                .insert(
                  uploadData.history.map(item => ({
                    ...item,
                    user_id: userId,
                    created_at: item.created_at || new Date().toISOString()
                  }))
                );
              if (!he) results.history = h;
            }
            
            if (uploadData.favorites) {
              const { data: f, error: fe } = await supabase
                .from('user_favorites')
                .upsert(
                  uploadData.favorites.map(item => ({
                    ...item,
                    user_id: userId
                  }))
                );
              if (!fe) results.favorites = f;
            }
            
            if (uploadData.settings) {
              const { data: s, error: se } = await supabase
                .from('user_settings')
                .upsert({
                  ...uploadData.settings,
                  user_id: userId,
                  updated_at: new Date().toISOString()
                });
              if (!se) results.settings = s;
            }
            
            result = results;
            break;
            
          default:
            return res.status(400).json({ 
              error: 'Invalid type',
              message: 'Supported types: history, favorite, settings, batch' 
            });
        }
        
        return res.status(200).json({
          success: true,
          message: 'Data synced successfully',
          result,
          timestamp: new Date().toISOString()
        });

      case 'DELETE':
        // 删除数据
        const { type: deleteType, id } = req.query;
        
        if (!deleteType || !id) {
          return res.status(400).json({ 
            error: 'Missing required parameters',
            message: 'Please provide type and id' 
          });
        }
        
        let deleteResult;
        
        switch (deleteType) {
          case 'history':
            const { error: historyDelError } = await supabase
              .from('user_history')
              .delete()
              .eq('user_id', userId)
              .eq('id', id);
            
            if (historyDelError) throw historyDelError;
            break;
            
          case 'favorite':
            const { error: favDelError } = await supabase
              .from('user_favorites')
              .delete()
              .eq('user_id', userId)
              .eq('id', id);
            
            if (favDelError) throw favDelError;
            break;
            
          default:
            return res.status(400).json({ 
              error: 'Invalid type',
              message: 'Supported types: history, favorite' 
            });
        }
        
        return res.status(200).json({
          success: true,
          message: 'Data deleted successfully',
          timestamp: new Date().toISOString()
        });

      default:
        return res.status(405).json({ error: 'Method not allowed' });
    }

  } catch (error) {
    console.error('Sync error:', error);
    return res.status(500).json({ 
      error: 'Sync failed',
      message: error.message 
    });
  }
};