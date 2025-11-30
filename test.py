import React, { useState, useEffect } from 'react';
import { Calendar, Clock, Store, ShoppingBag, FileText, Plus, Trash2, Download, Search } from 'lucide-react';

const GroupBuySystem = () => {
  const [currentPage, setCurrentPage] = useState('create');
  const [groups, setGroups] = useState([]);
  const [currentMenu, setCurrentMenu] = useState([
    { name: '範例:珍珠奶茶', price: 50 },
    { name: '範例:招牌便當', price: 100 }
  ]);
  const [loading, setLoading] = useState(true);

  // 載入資料
  useEffect(() => {
    loadData();
  }, []);

  // 儲存資料
  useEffect(() => {
    if (!loading) {
      saveData();
    }
  }, [groups]);

  const loadData = async () => {
    try {
      const result = await window.storage.get('group_buy_groups', false);
      if (result && result.value) {
        const data = JSON.parse(result.value);
        setGroups(data.map(g => ({
          ...g,
          deadline: new Date(g.deadline),
          createdAt: new Date(g.createdAt)
        })));
      }
    } catch (error) {
      console.log('首次載入或無資料');
    } finally {
      setLoading(false);
    }
  };

  const saveData = async () => {
    try {
      const dataToSave = groups.map(g => ({
        ...g,
        deadline: g.deadline.toISOString(),
        createdAt: g.createdAt.toISOString()
      }));
      await window.storage.set('group_buy_groups', JSON.stringify(dataToSave), false);
    } catch (error) {
      console.error('儲存失敗:', error);
    }
  };

  const addMenuItem = () => {
    setCurrentMenu([...currentMenu, { name: '', price: 0 }]);
  };

  const removeMenuItem = (index) => {
    setCurrentMenu(currentMenu.filter((_, i) => i !== index));
  };

  const updateMenuItem = (index, field, value) => {
    const newMenu = [...currentMenu];
    newMenu[index][field] = field === 'price' ? Number(value) : value;
    setCurrentMenu(newMenu);
  };

  const createGroup = (formData) => {
    const newGroup = {
      id: Date.now().toString(),
      vendorName: formData.vendorName,
      category: formData.category,
      description: formData.description,
      deadline: new Date(formData.deadline),
      menu: currentMenu.filter(item => item.name && item.price),
      orders: [],
      createdAt: new Date()
    };
    setGroups([...groups, newGroup]);
    setCurrentMenu([]);
    alert(`✅ 成功開團!店家:${formData.vendorName}`);
  };

  const addOrder = (groupId, orderData) => {
    setGroups(groups.map(g => {
      if (g.id === groupId) {
        return {
          ...g,
          orders: [...g.orders, {
            ...orderData,
            orderTime: new Date().toISOString()
          }]
        };
      }
      return g;
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-pink-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">載入中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-pink-50">
      {/* 導航欄 */}
      <nav className="bg-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-orange-600">🍱 多功能團購系統</h1>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentPage('create')}
                className={`px-4 py-2 rounded-lg transition ${
                  currentPage === 'create'
                    ? 'bg-orange-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                我要開團
              </button>
              <button
                onClick={() => setCurrentPage('order')}
                className={`px-4 py-2 rounded-lg transition ${
                  currentPage === 'order'
                    ? 'bg-orange-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                我要點餐
              </button>
              <button
                onClick={() => setCurrentPage('manage')}
                className={`px-4 py-2 rounded-lg transition ${
                  currentPage === 'manage'
                    ? 'bg-orange-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                訂單管理
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {currentPage === 'create' && <CreateGroupPage currentMenu={currentMenu} setCurrentMenu={setCurrentMenu} addMenuItem={addMenuItem} removeMenuItem={removeMenuItem} updateMenuItem={updateMenuItem} createGroup={createGroup} />}
        {currentPage === 'order' && <OrderPage groups={groups} addOrder={addOrder} />}
        {currentPage === 'manage' && <ManagePage groups={groups} />}
      </div>
    </div>
  );
};

// 開團頁面
const CreateGroupPage = ({ currentMenu, setCurrentMenu, addMenuItem, removeMenuItem, updateMenuItem, createGroup }) => {
  const [formData, setFormData] = useState({
    vendorName: '',
    category: '餐點',
    description: '',
    deadline: ''
  });

  const handleSubmit = () => {
    if (!formData.vendorName) {
      alert('❌ 請輸入店家名稱!');
      return;
    }
    if (currentMenu.filter(m => m.name && m.price).length === 0) {
      alert('❌ 菜單為空!請輸入至少一個品項。');
      return;
    }
    if (new Date(formData.deadline) <= new Date()) {
      alert('⛔ 收單時間不能早於目前時間!');
      return;
    }
    createGroup(formData);
    setFormData({ vendorName: '', category: '餐點', description: '', deadline: '' });
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-8">
      <h2 className="text-3xl font-bold text-gray-800 mb-6">我是團主:發起新團購</h2>
      
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">店家名稱 (必填)</label>
            <input
              type="text"
              value={formData.vendorName}
              onChange={(e) => setFormData({...formData, vendorName: e.target.value})}
              placeholder="例如:50嵐、八方雲集"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">團購分類</label>
            <select
              value={formData.category}
              onChange={(e) => setFormData({...formData, category: e.target.value})}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            >
              <option>餐點</option>
              <option>飲料</option>
              <option>其他</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">說明備註</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({...formData, description: e.target.value})}
            placeholder="例如:這家很快,要在11點前送單,請大家配合。"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
            rows="3"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">收單時間</label>
          <input
            type="datetime-local"
            value={formData.deadline}
            onChange={(e) => setFormData({...formData, deadline: e.target.value})}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
          />
        </div>

        <div className="border-t pt-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-semibold text-gray-800">菜單設定</h3>
            <button
              onClick={addMenuItem}
              className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition"
            >
              <Plus size={20} />
              新增品項
            </button>
          </div>

          <div className="space-y-3">
            {currentMenu.map((item, index) => (
              <div key={index} className="flex gap-3 items-center">
                <input
                  type="text"
                  value={item.name}
                  onChange={(e) => updateMenuItem(index, 'name', e.target.value)}
                  placeholder="品名"
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                />
                <input
                  type="number"
                  value={item.price}
                  onChange={(e) => updateMenuItem(index, 'price', e.target.value)}
                  placeholder="價格"
                  className="w-32 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                />
                <button
                  onClick={() => removeMenuItem(index)}
                  className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition"
                >
                  <Trash2 size={20} />
                </button>
              </div>
            ))}
          </div>
        </div>

        <button
          onClick={handleSubmit}
          className="w-full bg-orange-500 text-white py-3 rounded-lg font-semibold hover:bg-orange-600 transition flex items-center justify-center gap-2"
        >
          🚀 確認發起團購
        </button>
      </div>
    </div>
  );
};

// 點餐頁面
const OrderPage = ({ groups, addOrder }) => {
  const [selectedGroupId, setSelectedGroupId] = useState('');
  const [orderForm, setOrderForm] = useState({
    userName: '',
    selectedItem: '',
    quantity: 1,
    sugar: '(請選擇)',
    ice: '(請選擇)',
    note: ''
  });
  const [searchTerm, setSearchTerm] = useState('');

  const activeGroups = groups.filter(g => g.deadline > new Date());
  const selectedGroup = groups.find(g => g.id === selectedGroupId);

  const filteredMenu = selectedGroup?.menu.filter(item => 
    item.name.toLowerCase().includes(searchTerm.toLowerCase())
  ) || [];

  const handleSubmit = () => {
    if (!orderForm.userName) {
      alert('❌ 請輸入姓名!');
      return;
    }
    if (!orderForm.selectedItem) {
      alert('❌ 請選擇一項餐點!');
      return;
    }
    if (selectedGroup?.category === '飲料' && (orderForm.sugar === '(請選擇)' || orderForm.ice === '(請選擇)')) {
      alert('❌ 飲料類別請務必選擇「甜度」與「冰塊」!');
      return;
    }

    const menuItem = selectedGroup.menu.find(m => m.name === orderForm.selectedItem);
    let finalNote = orderForm.note;
    if (selectedGroup?.category === '飲料') {
      const bevNote = `${orderForm.sugar}/${orderForm.ice}`;
      finalNote = orderForm.note ? `${bevNote}, ${orderForm.note}` : bevNote;
    }

    addOrder(selectedGroupId, {
      userName: orderForm.userName,
      itemName: menuItem.name,
      unitPrice: menuItem.price,
      quantity: orderForm.quantity,
      totalPrice: menuItem.price * orderForm.quantity,
      note: finalNote
    });

    alert(`✅ ${orderForm.userName},您的「${menuItem.name}」已訂購成功!`);
    setOrderForm({
      userName: '',
      selectedItem: '',
      quantity: 1,
      sugar: '(請選擇)',
      ice: '(請選擇)',
      note: ''
    });
    setSearchTerm('');
  };

  if (activeGroups.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-8 text-center">
        <p className="text-gray-600 text-lg">目前沒有任何進行中的團購活動</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-8">
      <h2 className="text-3xl font-bold text-gray-800 mb-6">👋 我要點餐</h2>

      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">請選擇要參加的團購</label>
        <select
          value={selectedGroupId}
          onChange={(e) => {
            setSelectedGroupId(e.target.value);
            setOrderForm({...orderForm, selectedItem: ''});
            setSearchTerm('');
          }}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
        >
          <option value="">請選擇...</option>
          {activeGroups.map(group => {
            const timeLeft = group.deadline - new Date();
            const hoursLeft = Math.floor(timeLeft / (1000 * 60 * 60));
            return (
              <option key={group.id} value={group.id}>
                🟢 {group.vendorName} ({group.category}) - 剩餘 {hoursLeft} 小時
              </option>
            );
          })}
        </select>
      </div>

      {selectedGroup && (
        <div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold text-lg mb-2">🏪 {selectedGroup.vendorName}</h3>
            <p className="text-sm text-gray-600">📅 截止時間: {selectedGroup.deadline.toLocaleString('zh-TW')}</p>
            {selectedGroup.description && (
              <p className="text-sm text-gray-700 mt-2">📢 團主備註: {selectedGroup.description}</p>
            )}
          </div>

          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">您的姓名 (必填)</label>
              <input
                type="text"
                value={orderForm.userName}
                onChange={(e) => setOrderForm({...orderForm, userName: e.target.value})}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">選擇餐點 (可輸入關鍵字搜尋)</label>
              <div className="relative mb-2">
                <Search className="absolute left-3 top-3 text-gray-400" size={20} />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="搜尋餐點..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                />
              </div>
              <select
                value={orderForm.selectedItem}
                onChange={(e) => setOrderForm({...orderForm, selectedItem: e.target.value})}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              >
                <option value="">請選擇餐點</option>
                {filteredMenu.map((item, idx) => (
                  <option key={idx} value={item.name}>
                    {item.name} (${item.price})
                  </option>
                ))}
              </select>
            </div>

            {selectedGroup.category === '飲料' && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <h4 className="font-semibold mb-3">🍹 飲料客製化選項 (必填)</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">甜度</label>
                    <select
                      value={orderForm.sugar}
                      onChange={(e) => setOrderForm({...orderForm, sugar: e.target.value})}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    >
                      <option>(請選擇)</option>
                      <option>正常糖</option>
                      <option>少糖 (7分)</option>
                      <option>半糖 (5分)</option>
                      <option>微糖 (3分)</option>
                      <option>一分糖</option>
                      <option>無糖</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">冰塊</label>
                    <select
                      value={orderForm.ice}
                      onChange={(e) => setOrderForm({...orderForm, ice: e.target.value})}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                    >
                      <option>(請選擇)</option>
                      <option>正常冰</option>
                      <option>少冰</option>
                      <option>微冰</option>
                      <option>去冰</option>
                      <option>完全去冰</option>
                      <option>溫</option>
                      <option>熱</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">數量</label>
                <input
                  type="number"
                  min="1"
                  value={orderForm.quantity}
                  onChange={(e) => setOrderForm({...orderForm, quantity: parseInt(e.target.value) || 1})}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">其他備註</label>
                <input
                  type="text"
                  value={orderForm.note}
                  onChange={(e) => setOrderForm({...orderForm, note: e.target.value})}
                  placeholder="例如:加珍珠"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                />
              </div>
            </div>

            <button
              onClick={handleSubmit}
              className="w-full bg-orange-500 text-white py-3 rounded-lg font-semibold hover:bg-orange-600 transition"
            >
              送出訂單
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

// 訂單管理頁面
const ManagePage = ({ groups }) => {
  const [selectedGroupId, setSelectedGroupId] = useState('');
  const selectedGroup = groups.find(g => g.id === selectedGroupId);

  if (groups.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-8 text-center">
        <p className="text-gray-600 text-lg">目前沒有資料</p>
      </div>
    );
  }

  const downloadCSV = () => {
    if (!selectedGroup || selectedGroup.orders.length === 0) return;

    const headers = ['姓名', '品項', '單價', '數量', '總價', '備註', '下單時間'];
    const rows = selectedGroup.orders.map(order => [
      order.userName,
      order.itemName,
      order.unitPrice,
      order.quantity,
      order.totalPrice,
      order.note,
      order.orderTime
    ]);

    const csv = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `orders_${selectedGroup.vendorName}.csv`;
    link.click();
  };

  const summary = selectedGroup?.orders.reduce((acc, order) => {
    const key = `${order.itemName}|${order.note}`;
    if (!acc[key]) {
      acc[key] = { itemName: order.itemName, note: order.note, quantity: 0 };
    }
    acc[key].quantity += order.quantity;
    return acc;
  }, {});

  return (
    <div className="bg-white rounded-xl shadow-lg p-8">
      <h2 className="text-3xl font-bold text-gray-800 mb-6">📊 訂單管理與統計</h2>

      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">選擇要檢視的團購</label>
        <select
          value={selectedGroupId}
          onChange={(e) => setSelectedGroupId(e.target.value)}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
        >
          <option value="">請選擇...</option>
          {groups.map(group => {
            const status = group.deadline > new Date() ? '🟢進行中' : '🔴已截止';
            return (
              <option key={group.id} value={group.id}>
                {status} | {group.vendorName} ({group.category})
              </option>
            );
          })}
        </select>
      </div>

      {selectedGroup && (
        <div>
          <h3 className="text-2xl font-semibold mb-4">店家: {selectedGroup.vendorName}</h3>
          
          {selectedGroup.orders.length === 0 ? (
            <p className="text-gray-600">尚無訂單</p>
          ) : (
            <div className="space-y-6">
              <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                <div className="text-3xl font-bold text-green-700">
                  ${selectedGroup.orders.reduce((sum, o) => sum + o.totalPrice, 0)}
                </div>
                <div className="text-sm text-gray-600 mt-1">
                  共 {selectedGroup.orders.reduce((sum, o) => sum + o.quantity, 0)} 份餐點
                </div>
              </div>

              <div>
                <h4 className="text-xl font-semibold mb-3">詳細訂單列表</h4>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border px-4 py-2 text-left">姓名</th>
                        <th className="border px-4 py-2 text-left">品項</th>
                        <th className="border px-4 py-2 text-right">單價</th>
                        <th className="border px-4 py-2 text-right">數量</th>
                        <th className="border px-4 py-2 text-right">總價</th>
                        <th className="border px-4 py-2 text-left">備註</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedGroup.orders.map((order, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="border px-4 py-2">{order.userName}</td>
                          <td className="border px-4 py-2">{order.itemName}</td>
                          <td className="border px-4 py-2 text-right">${order.unitPrice}</td>
                          <td className="border px-4 py-2 text-right">{order.quantity}</td>
                          <td className="border px-4 py-2 text-right">${order.totalPrice}</td>
                          <td className="border px-4 py-2">{order.note}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h4 className="text-xl font-semibold mb-3">📝 廠商叫貨單 (合併相同品項與需求)</h4>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border px-4 py-2 text-left">品項</th>
                        <th className="border px-4 py-2 text-left">備註</th>
                        <th className="border px-4 py-2 text-right">數量</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.values(summary).map((item, idx) => (
                        <tr key={idx} className="hover:bg-gray-50">
                          <td className="border px-4 py-2">{item.itemName}</td>
                          <td className="border px-4 py-2">{item.note}</td>
                          <td className="border px-4 py-2 text-right">{item.quantity}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <button
                onClick={downloadCSV}
                className="flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
              >
                <Download size={20} />
                下載 [{selectedGroup.vendorName}] 訂單 CSV
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default GroupBuySystem;
