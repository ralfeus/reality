lastWeek = new Date(); 
lastWeek.setDate(lastWeek.getDate() - 7);
lastWeek.setHours(0, 0, 0, 0);

db.product.aggregate([
	{$match: {
		timeAdded: {$gt: lastWeek}
	}}, 
	{$group: {
		_id: "$id", 
		count: {$sum: 1}, 
		vendor: {$first: "$vendor"}, 
		layout: {$first: "$layout"}, 
		totalFloorArea: {$first: "$totalFloorArea"}, 
		priceWithVAT: {$first: "$priceWithVAT"}, 
		latitude: {$last: "$latitude"}, 
		longitude: {$last: "$longitude"}, 
		id: {$first: "$id"}, 
		timeAdded: {$first: "$timeAdded"}
	}},
	{$out: "sell-actual"}
]);

db.sreality_rent.aggregate([
	{$match: {
		timeAdded: {$gt: lastWeek}
	}}, 
	{$group: {
		_id: "$hash_id", 
		count: {$sum: 1}, 
		price: {$first: "$price"}, 
		latitude: {$last: "$gps.lat"}, 
		longitude: {$last: "$gps.lon"}, 
		id: {$first: "$hash_id"}, 
		name: {$first: "$name"},
		timeAdded: {$first: "$timeAdded"},
		dateAdded: {$first: "$dateAdded"}
	}}, 
	{$out: "rent-actual"}]);
